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
from pynput.keyboard import Controller, Key

class WhisperSharkGUI:
    # Unicode symbols that work well across platforms
    ICON_RECORD = "⏺"  # Record dot
    ICON_STOP = "⏹"    # Stop square
    ICON_COPY = "⎘"    # Copy symbol
    ICON_CLOSE = "✕"   # Clean X
    ICON_TYPE = "⌨"    # Keyboard icon
    
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
        
        # Initialize keyboard controller
        self.keyboard = Controller()
        
        # Recording variables
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.recording_thread = None
        self.sample_rate = 44100
        self.stream = None
        self._recording_lock = threading.Lock()
        self.accumulated_audio = []
        self.last_process_time = 0
        self.PROCESS_INTERVAL = 2.0  # Process every 2 seconds
        
        # Mode settings
        self.type_mode = True  # True for typing, False for clipboard
        
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
        self.title_bar.grid(row=0, column=0, columnspan=4, sticky="ew")
        
        title_label = ttk.Label(
            self.title_bar,
            text="Whisper Shark",
            style="Title.TLabel"
        )
        title_label.grid(row=0, column=0, padx=5, pady=2)
        
        # Mode toggle button
        self.mode_button = ttk.Button(
            self.title_bar,
            text=self.ICON_TYPE,
            width=2,
            command=self.toggle_mode,
            style="Icon.TButton"
        )
        self.mode_button.grid(row=0, column=1, padx=5, pady=1)
        
        # Close button
        close_button = ttk.Button(
            self.title_bar,
            text=self.ICON_CLOSE,
            width=2,
            command=self.on_closing,
            style="Icon.TButton"
        )
        close_button.grid(row=0, column=2, sticky="e", padx=(0,1), pady=1)
        
        # Control frame
        control_frame = ttk.Frame(main_frame, style="Main.TFrame")
        control_frame.grid(row=1, column=0, columnspan=4, sticky="ew")
        
        # Record button
        self.record_button = ttk.Button(
            control_frame,
            text=self.ICON_RECORD,
            width=2,
            command=self.toggle_recording,
            style="Record.TButton"
        )
        self.record_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Status label
        self.status_label = ttk.Label(
            control_frame,
            text="Ready",
            style="Status.TLabel"
        )
        self.status_label.grid(row=0, column=1, padx=5, pady=5)
        
        # Copy button
        self.copy_button = ttk.Button(
            control_frame,
            text=self.ICON_COPY,
            width=2,
            command=self.copy_last_text,
            state='disabled',
            style="Copy.TButton"
        )
        self.copy_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
            
    def toggle_mode(self):
        """Toggle between typing and clipboard modes"""
        self.type_mode = not self.type_mode
        if self.type_mode:
            self.mode_button.configure(text=self.ICON_TYPE)
            self.status_label.configure(text="Type mode: Text will be typed")
        else:
            self.mode_button.configure(text=self.ICON_COPY)
            self.status_label.configure(text="Copy mode: Text will be copied")
        self.root.after(2000, lambda: self.status_label.configure(text="Ready"))
            
    def process_audio_chunk(self):
        """Process accumulated audio if enough time has passed"""
        current_time = time.time()
        if (current_time - self.last_process_time >= self.PROCESS_INTERVAL and 
            self.accumulated_audio and self.is_recording):
            
            # Create a copy of accumulated audio and clear the original
            audio_to_process = np.concatenate(self.accumulated_audio.copy(), axis=0)
            self.accumulated_audio = []
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                try:
                    sf.write(temp_file.name, audio_to_process, self.sample_rate)
                    result = self.model.transcribe(temp_file.name)
                    
                    # Type or copy the text
                    if result["text"].strip():
                        self.handle_transcribed_text(result["text"], intermediate=True)
                        
                except Exception as e:
                    self.logger.error(f"Error processing audio chunk: {str(e)}")
                finally:
                    try:
                        os.unlink(temp_file.name)
                    except Exception as e:
                        self.logger.error(f"Error deleting temp file: {str(e)}")
                        
            self.last_process_time = current_time
            
    def handle_transcribed_text(self, text, intermediate=False):
        """Handle transcribed text based on current mode"""
        if not text.strip():
            return
            
        self.last_transcribed_text = text
        
        if self.type_mode:
            # In type mode, type the text directly
            if intermediate:
                # For intermediate chunks, add a space after
                self.keyboard.type(text + " ")
            else:
                # For final chunk, add newline
                self.keyboard.type(text + "\n")
        else:
            # In copy mode, copy to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_label.configure(text="Copied!")
            
        # Enable copy button
        self.copy_button.configure(state='normal')
            
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
            self.accumulated_audio.append(indata.copy())
            self.process_audio_chunk()
        except Exception as e:
            self.logger.error(f"Error in audio callback: {str(e)}")
            
    def start_recording(self):
        """Start recording with error handling"""
        try:
            self.is_recording = True
            self.record_button.configure(text=self.ICON_STOP)
            self.status_label.configure(text="Recording...")
            self.accumulated_audio = []
            self.last_process_time = time.time()
            
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
            self.status_label.configure(text="Processing final chunk...")
            
            # Wait for recording thread to finish with timeout
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=2.0)
                
            # Process any remaining audio
            if self.accumulated_audio:
                audio_data = np.concatenate(self.accumulated_audio, axis=0)
                self.accumulated_audio = []
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                    try:
                        sf.write(temp_file.name, audio_data, self.sample_rate)
                        
                        # Transcribe
                        result = self.model.transcribe(temp_file.name)
                        if result["text"].strip():
                            self.handle_transcribed_text(result["text"], intermediate=False)
                            
                        self.status_label.configure(text="Ready")
                        
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
