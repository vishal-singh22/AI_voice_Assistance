/**
 * Enhanced WebSocket client for voice interview
 * Features: Voice visualizer, real-time transcription, seamless audio streaming
 */

let websocket = null;
let audioContext = null;
let analyser = null;
let animationId = null;
let scriptProcessor = null;
let mediaStream = null;

// MediaSource-based audio playback (seamless streaming)
let mediaSource = null;
let sourceBuffer = null;
let audioElement = null;
let audioDataQueue = [];
let isAudioInitialized = false;

// Transcript management
let currentTranscript = '';
let transcriptParts = [];

function initializeInterview(candidateId) {
    connectWebSocket(candidateId);
    setupAudioCapture();
    initializeAudioPlayer();
}

function connectWebSocket(candidateId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/interview/${candidateId}`;
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = () => {
        console.log('WebSocket connected');
        updateStatus('connected', 'Connected - Interview starting...');
    };
    
    websocket.onmessage = (event) => {
        handleWebSocketMessage(event);
    };
    
    websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateStatus('error', 'Connection error');
    };
    
    websocket.onclose = () => {
        console.log('WebSocket closed');
        stopAudioCapture();
        stopAudioPlayer();
        updateStatus('disconnected', 'Connection closed');
    };
}

function handleWebSocketMessage(event) {
    // Handle binary data (audio from TTS)
    if (event.data instanceof Blob) {
        playAudio(event.data);
        return;
    }
    
    // Handle JSON messages
    try {
        const message = JSON.parse(event.data);
        
        switch (message.type) {
            case 'question':
                displayQuestion(message);
                break;
                
            case 'assistant':
                displayAssistantMessage(message.content);
                updateStatus('speaking', message.content);
                break;
                
            case 'transcript_interim':
                displayTranscript(message.content, true);
                break;
                
            case 'transcript_final':
                displayTranscript(message.content, false);
                break;
                
            case 'speech_final':
                handleSpeechFinal(message.content);
                break;
                
            case 'ready_for_answer':
                updateStatus('listening', '🎤 Listening for your answer...');
                clearTranscript();
                break;
                
            case 'answer_received':
                const scoreText = `Score: ${message.score}/100 (${message.keywords_matched} keywords matched)`;
                updateStatus('success', scoreText);
                break;
                
            case 'tts_start':
                updateStatus('speaking', 'Speaking...');
                break;
                
            case 'tts_end':
                updateStatus('listening', 'Ready for your answer...');
                break;
                
            case 'question_timeout':
                updateStatus('warning', message.message);
                setTimeout(() => clearTranscript(), 2000);
                break;
                
            case 'complete':
                handleInterviewComplete(message);
                break;
                
            case 'timeout':
                handleTimeout(message);
                break;
                
            case 'error':
                handleError(message);
                break;
                
            default:
                console.log('Unknown message type:', message.type, message);
        }
    } catch (error) {
        console.error('Error parsing message:', error);
    }
}

function displayQuestion(message) {
    document.getElementById('currentQuestion').textContent = message.number;
    document.getElementById('totalQuestions').textContent = message.total;
    document.getElementById('questionText').textContent = message.content;
    clearTranscript();
    updateStatus('speaking', 'Asking question...');
    document.getElementById('endButton').disabled = false;
}

function displayAssistantMessage(content) {
    console.log('Assistant:', content);
}

function displayTranscript(text, isInterim) {
    const transcriptEl = document.getElementById('transcriptText');
    
    if (isInterim) {
        // Show interim in gray/dim color
        transcriptEl.innerHTML = currentTranscript + 
            `<span style="color: #94a3b8; font-style: italic;">${text}</span>`;
    } else {
        // Add to permanent transcript
        transcriptParts.push(text);
        currentTranscript = transcriptParts.join(' ');
        transcriptEl.textContent = currentTranscript;
        transcriptEl.className = 'transcript-text';
    }
}

function handleSpeechFinal(fullTranscript) {
    console.log('Full transcript:', fullTranscript);
    updateStatus('processing', 'Processing your answer...');
    
    // Display final transcript
    const transcriptEl = document.getElementById('transcriptText');
    transcriptEl.textContent = fullTranscript;
    transcriptEl.className = 'transcript-text';
}

function clearTranscript() {
    currentTranscript = '';
    transcriptParts = [];
    const transcriptEl = document.getElementById('transcriptText');
    transcriptEl.textContent = 'Speak your answer...';
    transcriptEl.className = 'transcript-text';
}

function handleInterviewComplete(message) {
    updateStatus('complete', 'Interview Complete!');
    document.getElementById('questionText').textContent = message.message;
    document.getElementById('endButton').disabled = true;
    
    // Stop visualizer and audio
    stopVisualizer();
    stopAudioPlayer();
    
    // Redirect to results after 3 seconds
    setTimeout(() => {
        const candidateId = window.location.pathname.split('/').pop();
        window.location.href = `/candidate/result/${candidateId}`;
    }, 3000);
}

function handleTimeout(message) {
    updateStatus('error', 'Time Limit Reached');
    alert('Interview time limit reached. Your answers have been saved.');
    stopVisualizer();
    stopAudioPlayer();
    setTimeout(() => {
        const candidateId = window.location.pathname.split('/').pop();
        window.location.href = `/candidate/result/${candidateId}`;
    }, 2000);
}

function handleError(message) {
    updateStatus('error', 'Error Occurred');
    alert(message.message || 'An error occurred during the interview');
}

function updateStatus(status, text) {
    const indicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    // Remove all status classes
    indicator.className = 'status-indicator';
    
    // Add new status class
    indicator.classList.add(`status-${status}`);
    statusText.textContent = text;
}

// ========== Audio Capture with Visualizer ==========

async function setupAudioCapture() {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 16000
            }
        });
        
        // Create audio context for processing
        audioContext = new AudioContext({ sampleRate: 16000 });
        const source = audioContext.createMediaStreamSource(mediaStream);
        
        // Create analyser for visualization
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.8;
        source.connect(analyser);
        
        // Create script processor for sending audio to backend
        scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
        source.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination);
        
        scriptProcessor.onaudioprocess = (e) => {
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                const inputData = e.inputBuffer.getChannelData(0);
                const pcm16 = convertFloat32ToInt16(inputData);
                websocket.send(pcm16);
            }
        };
        
        // Start visualizer
        startVisualizer();
        
        console.log('Audio capture started with visualizer');
        updateStatus('connected', 'Microphone connected');
        
    } catch (error) {
        console.error('Error accessing microphone:', error);
        alert('Unable to access microphone. Please check your permissions and try again.');
        updateStatus('error', 'Microphone access denied');
    }
}

function convertFloat32ToInt16(float32Array) {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
        const s = Math.max(-1, Math.min(1, float32Array[i]));
        int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Array.buffer;
}

function stopAudioCapture() {
    // Stop media stream
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
    
    // Disconnect script processor
    if (scriptProcessor) {
        scriptProcessor.disconnect();
        scriptProcessor = null;
    }
    
    // Close audio context
    if (audioContext && audioContext.state !== 'closed') {
        audioContext.close();
        audioContext = null;
    }
    
    // Stop visualizer
    stopVisualizer();
}

// ========== Voice Visualizer ==========

function startVisualizer() {
    const canvas = document.getElementById('voiceVisualizer');
    if (!canvas || !analyser) return;
    
    const ctx = canvas.getContext('2d');
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    // Set canvas size
    canvas.width = canvas.offsetWidth;
    canvas.height = 60;
    
    function draw() {
        animationId = requestAnimationFrame(draw);
        
        // Get frequency data
        analyser.getByteFrequencyData(dataArray);
        
        // Clear canvas with fade effect
        ctx.fillStyle = 'rgba(15, 23, 42, 0.2)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Calculate bar width
        const barWidth = (canvas.width / bufferLength) * 2.5;
        let x = 0;
        
        // Draw frequency bars
        for (let i = 0; i < bufferLength; i++) {
            const barHeight = (dataArray[i] / 255) * canvas.height * 0.8;
            
            // Create gradient color (blue to cyan)
            const hue = 200 + (i / bufferLength) * 60;
            const brightness = 50 + (dataArray[i] / 255) * 50;
            
            ctx.fillStyle = `hsl(${hue}, 80%, ${brightness}%)`;
            ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
            
            x += barWidth + 1;
        }
    }
    
    draw();
}

function stopVisualizer() {
    if (animationId) {
        cancelAnimationFrame(animationId);
        animationId = null;
    }
    
    // Clear canvas
    const canvas = document.getElementById('voiceVisualizer');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
}

// ========== Seamless Audio Playback with MediaSource ==========

function initializeAudioPlayer() {
    if (isAudioInitialized) return;
    
    try {
        // Create MediaSource
        mediaSource = getMediaSource();
        if (!mediaSource) {
            console.error('MediaSource not supported');
            return;
        }
        
        mediaSource.addEventListener('sourceopen', handleSourceOpen);
        
        // Create audio element
        const audioUrl = URL.createObjectURL(mediaSource);
        audioElement = new Audio(audioUrl);
        
        // Start playing (will buffer first)
        audioElement.play().catch(err => {
            console.log('Audio autoplay prevented, will play on first audio chunk');
        });
        
        isAudioInitialized = true;
        console.log('Audio player initialized');
        
    } catch (error) {
        console.error('Error initializing audio player:', error);
    }
}

function handleSourceOpen() {
    // Check if MPEG audio is supported
    if (!MediaSource.isTypeSupported('audio/mpeg')) {
        console.error('MPEG audio not supported');
        return;
    }
    
    try {
        sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
        
        sourceBuffer.addEventListener('updateend', () => {
            // Process next audio chunk from queue
            if (audioDataQueue.length > 0 && !sourceBuffer.updating) {
                const nextChunk = audioDataQueue.shift();
                try {
                    sourceBuffer.appendBuffer(nextChunk);
                } catch (err) {
                    console.error('Error appending buffer:', err);
                }
            }
        });
        
        sourceBuffer.addEventListener('error', (e) => {
            console.error('SourceBuffer error:', e);
        });
        
        console.log('SourceBuffer created successfully');
        
    } catch (error) {
        console.error('Error creating SourceBuffer:', error);
    }
}

async function playAudio(audioBlob) {
    try {
        // Initialize player if not already done
        if (!isAudioInitialized) {
            initializeAudioPlayer();
            // Wait a bit for initialization
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        // Convert blob to ArrayBuffer
        const arrayBuffer = await audioBlob.arrayBuffer();
        const uint8Array = new Uint8Array(arrayBuffer);
        
        // Add to queue
        audioDataQueue.push(uint8Array);
        
        // If sourceBuffer is ready and not updating, append immediately
        if (sourceBuffer && !sourceBuffer.updating && audioDataQueue.length === 1) {
            try {
                sourceBuffer.appendBuffer(audioDataQueue.shift());
            } catch (err) {
                console.error('Error appending first buffer:', err);
                // Put it back in queue
                audioDataQueue.unshift(uint8Array);
            }
        }
        
        // Ensure audio is playing
        if (audioElement && audioElement.paused) {
            audioElement.play().catch(err => {
                console.log('Audio play error:', err);
            });
        }
        
    } catch (error) {
        console.error('Error processing audio:', error);
    }
}

function stopAudioPlayer() {
    try {
        // Pause and cleanup audio element
        if (audioElement) {
            audioElement.pause();
            audioElement.currentTime = 0;
            URL.revokeObjectURL(audioElement.src);
            audioElement = null;
        }
        
        // Remove source buffer
        if (sourceBuffer && mediaSource) {
            try {
                if (mediaSource.readyState === 'open') {
                    mediaSource.removeSourceBuffer(sourceBuffer);
                }
            } catch (err) {
                console.log('Error removing source buffer:', err);
            }
            sourceBuffer = null;
        }
        
        // End media source
        if (mediaSource) {
            try {
                if (mediaSource.readyState === 'open') {
                    mediaSource.endOfStream();
                }
            } catch (err) {
                console.log('Error ending media source:', err);
            }
            mediaSource = null;
        }
        
        // Clear queue
        audioDataQueue = [];
        isAudioInitialized = false;
        
        console.log('Audio player stopped');
        
    } catch (error) {
        console.error('Error stopping audio player:', error);
    }
}

function getMediaSource() {
    if ('MediaSource' in window) {
        return new MediaSource();
    } else if ('ManagedMediaSource' in window) {
        // Use ManagedMediaSource if available (iOS Safari)
        return new ManagedMediaSource();
    } else {
        console.error('No MediaSource API available');
        return null;
    }
}

// ========== Controls ==========

function endInterview() {
    if (confirm('Are you sure you want to end the interview? Your progress will be saved.')) {
        stopAudioCapture();
        stopAudioPlayer();
        
        if (websocket) {
            websocket.close();
        }
        
        // Redirect to results
        const candidateId = window.location.pathname.split('/').pop();
        setTimeout(() => {
            window.location.href = `/candidate/result/${candidateId}`;
        }, 500);
    }
}

// ========== Cleanup ==========

window.addEventListener('beforeunload', () => {
    stopAudioCapture();
    stopAudioPlayer();
    if (websocket) {
        websocket.close();
    }
});

// Handle window resize for canvas
window.addEventListener('resize', () => {
    const canvas = document.getElementById('voiceVisualizer');
    if (canvas) {
        canvas.width = canvas.offsetWidth;
    }
});