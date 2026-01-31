"""
Terminal-based interview demo
Uses local_assistant.py for voice interaction
Fixed configuration: 5 questions from JSON database
"""
import asyncio
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from app import questions, scoring
from app.config import settings

# Import specific functions from local_assistant
import re
import string
import requests
import wave
import pyaudio
from groq import AsyncGroq
from deepgram import (
    DeepgramClient, DeepgramClientOptions, LiveTranscriptionEvents, LiveOptions, Microphone
)

console = Console()

# Fixed demo configuration
DEMO_ROLE = 'software_engineer'
DEMO_NUM_QUESTIONS = 5

SYSTEM_PROMPT = """You are a helpful and enthusiastic assistant. Speak in a human, conversational tone.
Keep your answers as short and concise as possible, like in a conversation, ideally no more than 120 characters.
"""

DEEPGRAM_TTS_URL = 'https://api.deepgram.com/v1/speak?model=aura-luna-en&encoding=linear16&sample_rate=24000'

groq = AsyncGroq(api_key=settings.GROQ_API_KEY)

# Create the Deepgram client
deepgram_config = DeepgramClientOptions(options={'keepalive': 'true'})
deepgram = DeepgramClient(settings.DEEPGRAM_API_KEY, config=deepgram_config)

# Configure Deepgram options for live transcription
dg_connection_options = LiveOptions(
    model='nova-2',
    language='en',
    smart_format=True,
    encoding='linear16',
    channels=1,
    sample_rate=16000,
    interim_results=True,
    utterance_end_ms='2000',
    vad_events=True,
    endpointing=800,
)


def text_to_speech(text):
    """Convert text to speech and play it"""
    try:
        headers = {
            'Authorization': f'Token {settings.DEEPGRAM_API_KEY}',
            'Content-Type': 'application/json'
        }
        res = requests.post(DEEPGRAM_TTS_URL, headers=headers, json={'text': text}, stream=True)
        
        if res.status_code != 200:
            console.print(f'[red]TTS Error: {res.status_code}[/red]')
            return
        
        with wave.open(res.raw, 'rb') as wf:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                frames_per_buffer=1024,
                output=True
            )
            while len(data := wf.readframes(1024)): 
                stream.write(data)
            
            stream.close()
            p.terminate()
    except Exception as e:
        console.print(f'[red]TTS Error: {e}[/red]')


async def transcribe_audio():
    """Transcribe audio from microphone"""
    transcript_parts = []
    full_transcript = ''
    transcription_complete = asyncio.Event()
    
    try:
        # Create a websocket connection to Deepgram
        # dg_connection = deepgram.listen.asyncwebsocket.v('1')
        dg_connection = deepgram.listen.asynclive.v('1')

        async def on_message(self, result, **kwargs):
            nonlocal transcript_parts, full_transcript
            sentence = result.channel.alternatives[0].transcript
            if len(sentence) == 0:
                return
            if result.is_final:
                # Collect final sentences
                transcript_parts.append(sentence)
                console.print(sentence, style='cyan', end=' ')
                
                # Sufficient silence detected - end of speech
                if result.speech_final:
                    full_transcript = ' '.join(transcript_parts)
                    console.print()  # New line
                    transcription_complete.set()
            else:
                # Show interim results on same line
                console.print(sentence, style='dim cyan', end='\r')
        
        async def on_utterance_end(self, utterance_end, **kwargs):
            nonlocal transcript_parts, full_transcript
            if len(transcript_parts) > 0:
                full_transcript = ' '.join(transcript_parts)
                console.print()  # New line
                transcription_complete.set()
        
        async def on_error(self, error, **kwargs):
            console.print(f'[red]Deepgram Error: {error}[/red]')
        
        # Register the event handlers
        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
        dg_connection.on(LiveTranscriptionEvents.Error, on_error)

        # Start the connection
        if await dg_connection.start(dg_connection_options) is False:
            console.print('[red]Failed to connect to Deepgram[/red]')
            return None
        
        # Open a microphone stream
        microphone = Microphone(dg_connection.send)
        microphone.start()
        
        console.print('[dim]🎤 Listening... (speak your answer)[/dim]')

        # Wait for the transcription to complete (with timeout)
        try:
            await asyncio.wait_for(transcription_complete.wait(), timeout=60.0)
        except asyncio.TimeoutError:
            console.print('[yellow]⏱️  Answer timeout - moving to next question[/yellow]')
        
        # Close the microphone and the Deepgram connection
        microphone.finish()
        await dg_connection.finish()
        
        return full_transcript if full_transcript else None
    
    except Exception as e:
        console.print(f'[red]Could not transcribe audio: {e}[/red]')
        return None


async def run_demo_interview():
    """Run a terminal-based demo interview"""
    
    # Display welcome banner
    console.print('\n')
    console.print(Panel.fit(
        '[bold cyan]Voice Interview System - Terminal Demo[/bold cyan]\n\n'
        f'[white]Role:[/white] {DEMO_ROLE.replace("_", " ").title()}\n'
        f'[white]Questions:[/white] {DEMO_NUM_QUESTIONS}\n'
        f'[white]Passing Score:[/white] {settings.PASSING_SCORE}%\n\n'
        '[dim]Speak clearly into your microphone after each question[/dim]',
        border_style='cyan',
        padding=(1, 2)
    ))
    
    # Load questions
    questions_list = questions.get_questions_for_role(DEMO_ROLE, DEMO_NUM_QUESTIONS)
    
    if not questions_list:
        console.print('[red]Error: No questions found for this role[/red]')
        console.print('[yellow]Make sure data/questions.json exists[/yellow]')
        return
    
    console.print(f'\n[green]✓ Loaded {len(questions_list)} questions[/green]\n')
    
    # Wait for user to be ready
    console.print('[yellow]Press Enter when you\'re ready to start...[/yellow]')
    input()
    
    # Store responses
    responses = []
    
    # Conduct interview
    for i, question_data in enumerate(questions_list, 1):
        console.print('\n' + '='*80 + '\n')
        
        # Display question number
        console.print(f'[bold yellow]Question {i} of {len(questions_list)}[/bold yellow]\n')
        
        # Display and speak the question
        question_text = question_data['question']
        console.print(f'[bold cyan]Q: {question_text}[/bold cyan]\n')
        
        # Speak the question
        text_to_speech(question_text)
        
        # Small pause after TTS
        await asyncio.sleep(0.5)
        
        # Get answer via voice
        answer = await transcribe_audio()
        
        if not answer or answer.strip() == '':
            console.print('[red]✗ No answer detected. Skipping question.[/red]')
            continue
        
        console.print(f'\n[green]Your answer:[/green] {answer}\n')
        
        # Score the answer
        score, matched_keywords = scoring.score_answer(
            answer,
            question_data['keywords']
        )
        
        responses.append({
            'question': question_text,
            'answer': answer,
            'score': score,
            'keywords': question_data['keywords'],
            'matched': matched_keywords
        })
        
        console.print(f'[blue]Score: {score:.1f}/100[/blue]')
        console.print(f'[dim]Keywords matched: {len(matched_keywords)}/{len(question_data["keywords"])}[/dim]')
        
        if matched_keywords:
            console.print(f'[dim]Matched: {", ".join(matched_keywords)}[/dim]')
    
    # Calculate final results
    if responses:
        console.print('\n' + '='*80 + '\n')
        console.print('[bold cyan]📊 Interview Complete![/bold cyan]\n')
        
        final_score = sum(r['score'] for r in responses) / len(responses)
        passed = final_score >= settings.PASSING_SCORE
        
        # Display results table
        table = Table(title='Results Summary', show_header=True, header_style='bold magenta', border_style='cyan')
        table.add_column('Question #', style='cyan', width=12)
        table.add_column('Score', justify='right', style='green', width=10)
        table.add_column('Keywords Matched', justify='center', width=20)
        
        for i, r in enumerate(responses, 1):
            score_style = 'green' if r['score'] >= settings.PASSING_SCORE else 'red'
            table.add_row(
                f'Question {i}',
                f'[{score_style}]{r["score"]:.1f}/100[/{score_style}]',
                f'{len(r["matched"])}/{len(r["keywords"])}'
            )
        
        console.print(table)
        
        # Display final score with style
        console.print('\n')
        result_style = 'bold green' if passed else 'bold red'
        result_text = '✓ PASS' if passed else '✗ FAIL'
        
        console.print(Panel.fit(
            f'[bold white]Final Score:[/bold white] [{result_style}]{final_score:.2f}%[/{result_style}]\n'
            f'[bold white]Result:[/bold white] [{result_style}]{result_text}[/{result_style}]',
            border_style='green' if passed else 'red',
            padding=(1, 2)
        ))
        
        if passed:
            console.print(f'\n[green]🎉 Congratulations! You scored above the passing threshold of {settings.PASSING_SCORE}%[/green]')
        else:
            console.print(f'\n[red]📉 You scored below the passing threshold of {settings.PASSING_SCORE}%[/red]')
        
        # Display detailed breakdown
        console.print('\n[bold]📝 Detailed Breakdown:[/bold]\n')
        for i, r in enumerate(responses, 1):
            console.print(f'[cyan]Q{i}:[/cyan] {r["question"]}')
            console.print(f'[green]A{i}:[/green] {r["answer"][:150]}{"..." if len(r["answer"]) > 150 else ""}')
            console.print(f'[blue]Score:[/blue] {r["score"]:.1f}/100')
            if r["matched"]:
                console.print(f'[yellow]Matched keywords:[/yellow] {", ".join(r["matched"])}')
            else:
                console.print(f'[red]Matched keywords: None[/red]')
            console.print()
    else:
        console.print('[red]No responses recorded.[/red]')


def main():
    """Main entry point"""
    try:
        console.print('[bold]Starting interview demo...[/bold]')
        asyncio.run(run_demo_interview())
        console.print('\n[bold green]✓ Interview session ended[/bold green]\n')
    except KeyboardInterrupt:
        console.print('\n\n[yellow]⚠️  Interview interrupted by user[/yellow]')
        sys.exit(0)
    except Exception as e:
        console.print(f'\n[red]❌ Error: {e}[/red]')
        import traceback
        console.print('[dim]' + traceback.format_exc() + '[/dim]')
        sys.exit(1)


if __name__ == '__main__':
    main()