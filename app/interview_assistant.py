import asyncio
import httpx
from starlette.websockets import WebSocketDisconnect, WebSocketState
from deepgram import (
    DeepgramClient, DeepgramClientOptions, LiveTranscriptionEvents, LiveOptions
)
from groq import AsyncGroq
from app.config import settings
from app import crud, scoring, questions
from app.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

DEEPGRAM_TTS_URL = 'https://api.deepgram.com/v1/speak?model=aura-asteria-en'

deepgram_config = DeepgramClientOptions(options={'keepalive': 'true'})
deepgram = DeepgramClient(settings.DEEPGRAM_API_KEY, config=deepgram_config)
dg_connection_options = LiveOptions(
    model='nova-2',
    language='en',
    smart_format=True,
    encoding='linear16',
    channels=1,
    sample_rate=16000,
    interim_results=True,
    utterance_end_ms='2000',  # Increased from 1000ms
    vad_events=True,
    endpointing=800,
)
groq = AsyncGroq(api_key=settings.GROQ_API_KEY)

class InterviewAssistant:
    """Extended assistant specifically for conducting interviews"""
    
    def __init__(self, websocket, candidate_id: int, interview_config: dict):
        self.websocket = websocket
        self.candidate_id = candidate_id
        self.interview_config = interview_config
        
        # Voice transcription
        self.transcript_parts = []
        self.transcript_queue = asyncio.Queue()
        
        # Interview state
        self.questions_list = []
        self.current_question_index = 0
        self.responses = []
        
        self.httpx_client = httpx.AsyncClient()
        self.finish_event = asyncio.Event()
        
        # Database session
        self.db = SessionLocal()
        
        # Deepgram connection
        self.dg_connection = None
        
        # Load questions
        self._load_questions()
    
    def _load_questions(self):
        """Load questions based on interview configuration"""
        role = self.interview_config['role']
        num_questions = self.interview_config['num_questions']
        use_llm = self.interview_config['use_llm']
        
        if use_llm:
            # For LLM mode, we'll generate questions on-the-fly
            self.questions_list = [{'question': None, 'keywords': []} for _ in range(num_questions)]
            logger.info(f'Interview will use LLM-generated questions ({num_questions} total)')
        else:
            # Load from JSON/DB
            self.questions_list = questions.get_questions_for_role(role, num_questions)
            logger.info(f'Loaded {len(self.questions_list)} questions for role: {role}')
    
    async def generate_llm_question(self, previous_qa: list = None) -> dict:
        """Generate a question using LLM"""
        role = self.interview_config['role']
        
        # Build context from previous Q&A
        context = ''
        if previous_qa:
            context = 'Previous questions and answers:\n'
            for qa in previous_qa[-3:]:  # Last 3 Q&A for context
                context += f"Q: {qa['question']}\nA: {qa['answer']}\n\n"
        
        prompt = f"""You are conducting a technical interview for a {role} position.
{context}
Generate ONE interview question for this role. The question should be clear, specific, and test technical knowledge.
Respond with only the question, nothing else."""
        
        try:
            response = await groq.chat.completions.create(
                messages=[{'role': 'user', 'content': prompt}],
                model=settings.LLM
            )
            question_text = response.choices[0].message.content.strip()
            
            # Generate keywords from the question
            keywords_prompt = f"""For this interview question: "{question_text}"
List 5-8 important keywords or concepts that a good answer should include.
Respond with only comma-separated keywords, nothing else."""
            
            keywords_response = await groq.chat.completions.create(
                messages=[{'role': 'user', 'content': keywords_prompt}],
                model=settings.LLM
            )
            keywords_text = keywords_response.choices[0].message.content.strip()
            keywords = [k.strip() for k in keywords_text.split(',')]
            
            return {'question': question_text, 'keywords': keywords}
        
        except Exception as e:
            logger.error(f'Error generating LLM question: {e}')
            # Fallback to a generic question
            return {
                'question': f'Tell me about your experience with {role} responsibilities.',
                'keywords': ['experience', 'skills', 'projects']
            }
    
    async def text_to_speech(self, text: str):
        """Convert text to speech - EXACT SAME AS local_assistant.py"""
        headers = {
            'Authorization': f'Token {settings.DEEPGRAM_API_KEY}',
            'Content-Type': 'application/json'
        }
        try:
            await self.websocket.send_json({'type': 'tts_start'})
            
            async with self.httpx_client.stream(
                'POST', DEEPGRAM_TTS_URL, headers=headers, json={'text': text}
            ) as res:
                async for chunk in res.aiter_bytes(1024):
                    await self.websocket.send_bytes(chunk)
            
            await self.websocket.send_json({'type': 'tts_end'})
            
        except Exception as e:
            logger.error(f'TTS error: {e}')
            await self.websocket.send_json({'type': 'tts_error', 'message': str(e)})
    
    async def transcribe_audio(self):
        """Transcribe audio from candidate"""
        async def on_message(self_handler, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if len(sentence) == 0:
                return
            
            if result.is_final:
                # Final transcript
                self.transcript_parts.append(sentence)
                await self.websocket.send_json({
                    'type': 'transcript_final',
                    'content': sentence
                })
                await self.transcript_queue.put({
                    'type': 'transcript_final',
                    'content': sentence
                })
                
                # Speech is complete
                if result.speech_final:
                    full_transcript = ' '.join(self.transcript_parts)
                    self.transcript_parts = []
                    await self.websocket.send_json({
                        'type': 'speech_final',
                        'content': full_transcript
                    })
                    await self.transcript_queue.put({
                        'type': 'speech_final',
                        'content': full_transcript
                    })
            else:
                # Interim transcript - show in real-time
                await self.websocket.send_json({
                    'type': 'transcript_interim',
                    'content': sentence
                })
        
        async def on_utterance_end(self_handler, utterance_end, **kwargs):
            if len(self.transcript_parts) > 0:
                full_transcript = ' '.join(self.transcript_parts)
                self.transcript_parts = []
                await self.websocket.send_json({
                    'type': 'speech_final',
                    'content': full_transcript
                })
                await self.transcript_queue.put({
                    'type': 'speech_final',
                    'content': full_transcript
                })

        self.dg_connection = deepgram.listen.asynclive.v('1')
        self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        self.dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
        
        if await self.dg_connection.start(dg_connection_options) is False:
            raise Exception('Failed to connect to Deepgram')
        
        try:
            while not self.finish_event.is_set():
                data = await self.websocket.receive_bytes()
                await self.dg_connection.send(data)
        except Exception as e:
            logger.error(f'Transcription error: {e}')
        finally:
            await self.dg_connection.finish()
    
    async def conduct_interview(self):
        """Main interview loop"""
        # Small delay to ensure transcription is ready
        await asyncio.sleep(1)
        
        # Send welcome message
        welcome = f"Welcome to your interview for {self.interview_config['role'].replace('_', ' ')}. Let's begin with the first question."
        await self.websocket.send_json({'type': 'assistant', 'content': welcome})
        await self.text_to_speech(welcome)
        
        # Wait for TTS to finish
        await asyncio.sleep(2)
        
        # Mark interview as started
        crud.update_candidate_status(self.db, self.candidate_id, has_started=True)
        
        # Ask each question
        while self.current_question_index < len(self.questions_list) and not self.finish_event.is_set():
            # Get or generate question
            if self.interview_config['use_llm'] and not self.questions_list[self.current_question_index]['question']:
                question_data = await self.generate_llm_question(self.responses)
                self.questions_list[self.current_question_index] = question_data
            else:
                question_data = self.questions_list[self.current_question_index]
            
            # Ask the question
            question_text = question_data['question']
            await self.websocket.send_json({
                'type': 'question',
                'content': question_text,
                'number': self.current_question_index + 1,
                'total': len(self.questions_list)
            })
            await self.text_to_speech(question_text)
            
            # Wait for TTS to finish before accepting answer
            await asyncio.sleep(1)
            
            # Clear any old transcript data
            while not self.transcript_queue.empty():
                try:
                    self.transcript_queue.get_nowait()
                except:
                    break
            
            # Signal ready for answer
            await self.websocket.send_json({'type': 'ready_for_answer'})
            
            # Wait for answer with timeout
            waiting_for_answer = True
            answer_timeout = 60  # 60 seconds per question
            
            try:
                async with asyncio.timeout(answer_timeout):
                    while waiting_for_answer and not self.finish_event.is_set():
                        transcript = await self.transcript_queue.get()
                        
                        if transcript['type'] == 'speech_final':
                            answer_text = transcript['content']
                            
                            # Ignore very short answers
                            if len(answer_text.strip()) < 5:
                                logger.warning(f'Answer too short: {answer_text}')
                                continue
                            
                            # Score the answer
                            score, matched_keywords = scoring.score_answer(
                                answer_text,
                                question_data['keywords']
                            )
                            
                            # Save to database
                            crud.create_response(
                                self.db,
                                candidate_id=self.candidate_id,
                                question_text=question_text,
                                answer_text=answer_text,
                                score=score,
                                keywords_found=matched_keywords
                            )
                            
                            # Store in memory
                            self.responses.append({
                                'question': question_text,
                                'answer': answer_text,
                                'score': score
                            })
                            
                            # Acknowledge
                            ack = "Thank you. Let's move to the next question."
                            await self.websocket.send_json({
                                'type': 'answer_received',
                                'score': score,
                                'keywords_matched': len(matched_keywords)
                            })
                            await self.text_to_speech(ack)
                            
                            # Wait before next question
                            await asyncio.sleep(2)
                            
                            waiting_for_answer = False
                            self.current_question_index += 1
            
            except asyncio.TimeoutError:
                logger.warning(f'Question {self.current_question_index + 1} timeout')
                await self.websocket.send_json({
                    'type': 'question_timeout',
                    'message': 'Time limit reached, moving to next question'
                })
                self.current_question_index += 1
        
        # Interview complete
        await self.finish_interview()
    
    async def finish_interview(self):
        """Finish the interview and calculate results"""
        # Calculate final score
        final_score = crud.calculate_final_score(self.db, self.candidate_id)
        passed = final_score >= settings.PASSING_SCORE
        
        # Update candidate
        crud.update_candidate_status(
            self.db,
            self.candidate_id,
            has_completed=True,
            score=final_score,
            passed=passed
        )
        
        # Send completion message
        result_message = f"Interview complete. Your score is {final_score:.1f}%. You have {'passed' if passed else 'not passed'}."
        await self.websocket.send_json({
            'type': 'complete',
            'score': final_score,
            'passed': passed,
            'message': result_message
        })
        await self.text_to_speech(result_message)
        
        self.finish_event.set()
        logger.info(f'Interview completed for candidate {self.candidate_id}. Score: {final_score}%')
    
    async def run(self):
        """Run the interview assistant"""
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.transcribe_audio())
                tg.create_task(self.conduct_interview())
        except* WebSocketDisconnect:
            logger.info(f'Candidate {self.candidate_id} disconnected')
        except* Exception as e:
            logger.error(f'Interview error: {e}')
        finally:
            await self.httpx_client.aclose()
            self.db.close()
            if self.websocket.client_state != WebSocketState.DISCONNECTED:
                await self.websocket.close()