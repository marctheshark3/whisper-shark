import tkinter as tk
from tkinter import ttk, font
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
import tempfile
import os
import time
import logging

class WhisperSharkGUI:
    # Unicode symbols that work well across platforms
    ICON_RECORD = "⏺"  # Record dot
    ICON_STOP = "⏹"    # Stop square
    ICON_COPY = "⎘"    # Copy symbol
    ICON_CLOSE = "✕"   # Clean X
    
    def __init__(self, root):
        self.root = root
        self.root.title("WhisperShark")
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('WhisperShark')
        
        # Configure styles
        self.setup_styles()
        
        # Make window stay on top
        self.root.attributes('-topmost', True)
        
        # Remove window decorations for a minimal look
        self.root.overrideredirect(True)
        
        # Load Whisper model
        self.model = whisper.load_model("base")
        
        # Recording variables
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.recording_thread = None
        self.sample_rate = 44100
        self.stream = None
        self._recording_lock = threading.Lock()
        
        self.create_widgets()
        self.setup_draggable()
        
        # Ensure cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_styles(self):
        """Configure custom styles for the GUI"""
        style = ttk.Style()
        
        # Configure main frame style
        style.configure("Main.TFrame", background='#2b2b2b')
        
        # Configure title bar style
        style.configure("Title.TFrame", background='#1e1e1e')
        style.configure("Title.TLabel", 
                       background='#1e1e1e',
                       foreground='#ffffff',
                       font=('Helvetica', 10, 'bold'))
        
        # Configure button styles
        style.configure("Icon.TButton",
                       font=('Helvetica', 12),
                       padding=2,
                       background='#363636',
                       relief='flat')
        
        style.configure("Record.TButton",
                       background='#363636',
                       foreground='#ff4444')
                       
        style.configure("Copy.TButton",
                       background='#363636',
                       foreground='#4444ff')
        
        # Configure status label style
        style.configure("Status.TLabel",
                       background='#2b2b2b',
                       foreground='#bbbbbb',
                       font=('Helvetica', 9))
        
    def on_closing(self):
        """Ensure proper cleanup when closing the application"""
        if self.is_recording:
            self.stop_recording()
        self.root.quit()
        
    def setup_draggable(self):
        def start_move(event):
            self.x = event.x
            self.y = event.y

        def stop_move(event):
            self.x = None
            self.y = None

        def do_move(event):
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.root.winfo_x() + deltax
            y = self.root.winfo_y() + deltay
            self.root.geometry(f"+{x}+{y}")

        self.title_bar.bind('<Button-1>', start_move)
        self.title_bar.bind('<ButtonRelease-1>', stop_move)
        self.title_bar.bind('<B1-Motion>', do_move)
        
    def create_widgets(self):
        # Main frame with border
        main_frame = ttk.Frame(self.root, padding="2", style="Main.TFrame")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Title bar for dragging
        self.title_bar = ttk.Frame(main_frame, style="Title.TFrame")
        self.title_bar.grid(row=0, column=0, columnspan=3, sticky="ew")
        
        title_label = ttk.Label(
            self.title_bar,
            text="Whisper Shark",
            style="Title.TLabel"
        )
        title_label.grid(row=0, column=0, padx=5, pady=2)
        
        # Close button
        close_button = ttk.Button(
            self.title_bar,
            text=self.ICON_CLOSE,
            width=2,
            command=self.on_closing,
            style="Icon.TButton"
        )
        close_button.grid(row=0, column=1, sticky="e", padx=(0,1), pady=1)
        
        # Record button
        self.record_button = ttk.Button(
            main_frame,
            text=self.ICON_RECORD,
            width=2,
            command=self.toggle_recording,
            style="Record.TButton"
        )
        self.record_button.grid(row=1, column=0, padx=5, pady=5)
        
        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="Ready",
            style="Status.TLabel"
        )
        self.status_label.grid(row=1, column=1, padx=5, pady=5)
        
        # Copy button
        self.copy_button = ttk.Button(
            main_frame,
            text=self.ICON_COPY,
            width=2,
            command=self.copy_last_text,
            state='disabled',
            style="Copy.TButton"
        )
        self.copy_button.grid(row=1, column=2, padx=5, pady=5)
        
        self.last_transcribed_text = None
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
            
    def copy_last_text(self):
        """Copy the last transcribed text to clipboard"""
        if self.last_transcribed_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.last_transcribed_text)
            self.status_label.configure(text="Copied!")
            self.root.after(2000, lambda: self.status_label.configure(text="Ready"))
            
    def toggle_recording(self):
        """Thread-safe recording toggle"""
        with self._recording_lock:
            if not self.is_recording:
                self.start_recording()
            else:
                self.stop_recording()
            
    def audio_callback(self, indata, frames, time, status):
        """Callback for audio data"""
        if status:
            self.logger.warning(f"Audio callback status: {status}")
        try:
            self.audio_queue.put(indata.copy())
        except Exception as e:
            self.logger.error(f"Error in audio callback: {str(e)}")
            
    def start_recording(self):
        """Start recording with error handling"""
        try:
            self.is_recording = True
            self.record_button.configure(text=self.ICON_STOP)
            self.status_label.configure(text="Recording...")
            self.copy_button.configure(state='disabled')
            
            # Clear the audio queue
            while not self.audio_queue.empty():
                self.audio_queue.get()
            
            def record_audio():
                try:
                    with sd.InputStream(
                        callback=self.audio_callback,
                        channels=1,
                        samplerate=self.sample_rate,
                        blocksize=int(self.sample_rate * 0.1)  # 100ms blocks
                    ) as self.stream:
                        while self.is_recording:
                            time.sleep(0.05)  # Reduced sleep time for better responsiveness
                            
                except Exception as e:
                    self.logger.error(f"Error in recording thread: {str(e)}")
                    self.root.after(0, lambda: self.status_label.configure(text=f"Error: {str(e)}"))
                finally:
                    self.is_recording = False
                    self.root.after(0, lambda: self.record_button.configure(text=self.ICON_RECORD))
                    
            self.recording_thread = threading.Thread(target=record_audio)
            self.recording_thread.start()
            
        except Exception as e:
            self.logger.error(f"Error starting recording: {str(e)}")
            self.status_label.configure(text=f"Error: {str(e)}")
            self.is_recording = False
            self.record_button.configure(text=self.ICON_RECORD)
        
    def stop_recording(self):
        """Stop recording and process audio"""
        try:
            self.is_recording = False
            self.status_label.configure(text="Processing...")
            
            # Wait for recording thread to finish with timeout
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=2.0)
                
            # Process recorded audio
            recorded_chunks = []
            try:
                while not self.audio_queue.empty():
                    recorded_chunks.append(self.audio_queue.get_nowait())
            except queue.Empty:
                pass
                
            if recorded_chunks:
                audio_data = np.concatenate(recorded_chunks, axis=0)
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                    try:
                        sf.write(temp_file.name, audio_data, self.sample_rate)
                        
                        # Transcribe
                        result = self.model.transcribe(temp_file.name)
                        self.last_transcribed_text = result["text"]
                        
                        # Enable copy button and update status
                        self.copy_button.configure(state='normal')
                        self.status_label.configure(text="Ready - Click to copy")
                        
                        # Automatically copy to clipboard
                        self.root.clipboard_clear()
                        self.root.clipboard_append(self.last_transcribed_text)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing audio: {str(e)}")
                        self.status_label.configure(text=f"Error: {str(e)}")
                    finally:
                        try:
                            os.unlink(temp_file.name)
                        except Exception as e:
                            self.logger.error(f"Error deleting temp file: {str(e)}")
            else:
                self.status_label.configure(text="No audio recorded")
                
        except Exception as e:
            self.logger.error(f"Error stopping recording: {str(e)}")
            self.status_label.configure(text=f"Error: {str(e)}")
        finally:
            self.record_button.configure(text=self.ICON_RECORD)

def main():
    try:
        root = tk.Tk()
        app = WhisperSharkGUI(root)
        # Start in top-right corner
        root.geometry(f"+{root.winfo_screenwidth()-200}+50")
        root.mainloop()
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
