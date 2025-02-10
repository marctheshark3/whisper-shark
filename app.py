import gradio as gr
import whisper

# Load the Whisper model (options include: tiny, base, small, medium, large)
model = whisper.load_model("base")

def transcribe(audio_file):
    """
    Transcribes the given audio file using the Whisper model.
    """
    if audio_file is None:
        return "No audio was provided. Please record your speech and try again."
    # Transcribe the audio file
    result = model.transcribe(audio_file)
    return result["text"]

# Create a Gradio interface with a record button for audio input
iface = gr.Interface(
    fn=transcribe,
    inputs=gr.Audio(source="microphone", type="filepath"),
    outputs="text",
    title="Whisper Speech-to-Text",
    description="Click the record button, speak, and view the transcription below."
)

if __name__ == "__main__":
    iface.launch()
