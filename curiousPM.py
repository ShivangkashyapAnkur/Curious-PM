import streamlit as st
import requests
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
from moviepy.editor import VideoFileClip, AudioFileClip
import tempfile


GPT_4O_API_KEY = "22ec84421ec24230a3638d1b51e3a7dc"
GPT_4O_ENDPOINT = "https://internshala.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview"

st.title("AI-Powered Video Audio Replacement")


video_file = st.file_uploader(
    "Upload a video file", type=["mp4", "mkv", "avi"])

if video_file:

    temp_video_path = tempfile.NamedTemporaryFile(
        delete=False, suffix='.mp4').name
    with open(temp_video_path, 'wb') as f:
        f.write(video_file.read())

    video_clip = VideoFileClip(temp_video_path)
    audio_clip = video_clip.audio
    temp_audio_path = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    audio_clip.write_audiofile(temp_audio_path)

    def transcribe_audio(audio_path):
        client = speech.SpeechClient()
        with open(audio_path, "rb") as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            language_code="en-US",
            model="default",
            enable_automatic_punctuation=True,
        )

        response = client.recognize(config=config, audio=audio)
        transcript = "".join(
            [result.alternatives[0].transcript for result in response.results])
        return transcript

    with st.spinner("Transcribing audio..."):
        transcription = transcribe_audio(temp_audio_path)
        st.write("Original Transcription:", transcription)

    def correct_transcription(transcript):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {GPT_4O_API_KEY}'
        }
        data = {
            "messages": [
                {"role": "system", "content": "You are an assistant that corrects grammar."},
                {"role": "user", "content": f"Please correct this transcription: {transcript}"}
            ]
        }
        response = requests.post(GPT_4O_ENDPOINT, headers=headers, json=data)
        corrected_transcription = response.json(
        )['choices'][0]['message']['content']
        return corrected_transcription

    with st.spinner("Correcting transcription..."):
        corrected_transcription = correct_transcription(transcription)
        st.write("Corrected Transcription:", corrected_transcription)

    def synthesize_speech(text, output_path):
        client = texttospeech.TextToSpeechClient()

        input_text = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-JennyNeural",
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )

        response = client.synthesize_speech(
            input=input_text, voice=voice, audio_config=audio_config
        )

        with open(output_path, "wb") as out:
            out.write(response.audio_content)

    temp_new_audio_path = tempfile.NamedTemporaryFile(
        delete=False, suffix='.wav').name
    with st.spinner("Synthesizing new audio..."):
        synthesize_speech(corrected_transcription, temp_new_audio_path)

    output_video_path = tempfile.NamedTemporaryFile(
        delete=False, suffix='.mp4').name
    with st.spinner("Replacing audio in video..."):
        final_audio_clip = AudioFileClip(temp_new_audio_path)
        final_video = video_clip.set_audio(final_audio_clip)
        final_video.write_videofile(output_video_path, codec="libx264")

    st.success("Audio replacement complete!")
    with open(output_video_path, "rb") as f:
        st.download_button("Download Modified Video", f,
                           file_name="modified_video.mp4")
