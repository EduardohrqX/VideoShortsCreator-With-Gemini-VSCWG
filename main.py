import os
import re
import json
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time

# Importar funções dos módulos dos módulos do projeto
from audio_processing import extract_audio, analyze_pitch
from transcription import transcribe_audio
from gemini_analysis import analyze_transcription_with_gemini
from subtitle_styler import stylize_transcription
from video_editing import cut_and_reformat_video, parse_timestamp_to_seconds

# --- Configurações da Aplicação ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class ShortsCreatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Gemini Shorts Creator")
        self.geometry("1000x900")

        # --- Variáveis de Estado ---
        self.gemini_api_key = ctk.StringVar(value=os.getenv("GOOGLE_API_KEY", ""))
        self.video_source_path = ctk.StringVar()
        self.output_base_dir = ctk.StringVar(value="shorts_final_output")
        self.min_duration = ctk.StringVar(value="5")
        self.max_duration = ctk.StringVar(value="60")
        self.enable_pitch_analysis = ctk.BooleanVar(value=False)
        self.transcription_language = ctk.StringVar(value="pt")
        
        # Variáveis de estado para legendas
        self.add_subtitles = ctk.BooleanVar(value=True)
        self.subtitle_font = ctk.StringVar(value="Impact")
        self.subtitle_color_theme = ctk.StringVar(value="Yellow/White")
        self.subtitle_animation_style = ctk.StringVar(value="Elastic-Jump")
        self.subtitle_add_emojis = ctk.BooleanVar(value=False)
        self.subtitle_font_size = ctk.StringVar(value="70")
        self.subtitle_position = ctk.StringVar(value="Inferior")
        self.remove_punctuation = ctk.BooleanVar(value=True)
        self.outline_thickness = ctk.StringVar(value="4")
        self.shadow_depth = ctk.StringVar(value="4")

        # --- Variáveis de Estado para Áudio e Exportação ---
        self.output_format_choice = ctk.StringVar(value="shorts_vertical")
        self.add_background_music = ctk.BooleanVar(value=False)
        self.music_folder_path = ctk.StringVar()
        self.music_volume_percent = ctk.DoubleVar(value=20.0)

        # --- Modos de Operação ---
        self.full_auto_mode = ctk.BooleanVar(value=False)
        self.chain_processing_mode = ctk.BooleanVar(value=False)

        self.highlights_data = []
        self.highlight_checkboxes = []
        self.current_highlight_video_path = None
        self.current_transcription_path = None # Para manter o controle do arquivo de transcrição atual

        # Register validation command for numeric inputs
        self.vcmd = (self.register(self._on_numeric_validate), '%P')

        self._create_widgets()

    def _on_numeric_validate(self, P):
        # P is the value of the entry if the edit is allowed
        if P.isdigit() or P == "":
            return True
        else:
            self._log_message("Aviso: Apenas números são permitidos neste campo.")
            return False

    def _validate_and_set_numeric_var(self, var, default_value):
        # This function is still useful for initial setup or programmatic changes
        value = var.get()
        if value == "":
            var.set(str(default_value))
        else:
            try:
                int(value)
            except ValueError:
                var.set(str(default_value))
                self._log_message(f"Aviso: Entrada inválida. Usando o padrão: {default_value}")

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Container Principal com Abas ---
        tab_view = ctk.CTkTabview(self, anchor="nw")
        tab_view.pack(pady=10, padx=10, fill="x")
        
        tab_config = tab_view.add("Configuração")
        tab_analise = tab_view.add("Análise & IA")
        tab_legendas = tab_view.add("Estilo das Legendas")
        tab_audio_export = tab_view.add("Áudio & Exportação")

        # --- Aba 1: Configuração ---
        self._create_config_tab(tab_config)

        # --- Aba 2: Análise & IA ---
        self._create_analise_tab(tab_analise)

        # --- Aba 3: Estilo das Legendas ---
        self._create_legendas_tab(tab_legendas)

        # --- Aba 4: Áudio & Exportação ---
        self._create_audio_export_tab(tab_audio_export)

        # --- Frame de Ações (Botões) ---
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(pady=10, padx=10, fill="x")
        action_frame.grid_columnconfigure((0, 1), weight=1)

        self.start_analysis_button = ctk.CTkButton(action_frame, text="Iniciar Análise", command=self._start_analysis_thread)
        self.start_analysis_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.process_selected_button = ctk.CTkButton(action_frame, text="Processar Highlights Selecionados", command=self._process_selected_highlights_thread, state="disabled")
        self.process_selected_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.full_auto_mode_checkbox = ctk.CTkCheckBox(action_frame, text="Modo Automático Completo (Processar todos os highlights)", variable=self.full_auto_mode, command=self._toggle_auto_mode)
        self.full_auto_mode_checkbox.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # --- Frame de Progresso e Logs ---
        progress_log_frame = ctk.CTkFrame(self)
        progress_log_frame.pack(pady=10, padx=10, fill="both", expand=True)
        progress_log_frame.grid_columnconfigure(0, weight=1)
        progress_log_frame.grid_rowconfigure(1, weight=1)

        self.progress_label = ctk.CTkLabel(progress_log_frame, text="Status: Ocioso")
        self.progress_label.grid(row=0, column=0, padx=10, pady=(5,0), sticky="w")
        self.progress_bar = ctk.CTkProgressBar(progress_log_frame, orientation="horizontal")
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=1, padx=10, pady=(5,0), sticky="ew")

        self.log_text = ctk.CTkTextbox(progress_log_frame, wrap="word", state="disabled")
        self.log_text.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        # --- Frame de Highlights (inicialmente oculto) ---
        self.highlights_main_frame = ctk.CTkFrame(self)
        # Não usar pack/grid aqui, será controlado dinamicamente

    def _create_config_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(tab, text="Chave da API Gemini:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(tab, textvariable=self.gemini_api_key, width=400).grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(tab, text="Vídeo ou Diretório de Vídeos:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(tab, textvariable=self.video_source_path).grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(tab, text="Procurar", command=self._browse_video_source).grid(row=1, column=2, padx=10, pady=10)

        ctk.CTkLabel(tab, text="Diretório de Saída:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(tab, textvariable=self.output_base_dir).grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(tab, text="Procurar", command=self._browse_output_dir).grid(row=2, column=2, padx=10, pady=10)

        ctk.CTkCheckBox(tab, text="Processamento em Cadeia (Ativa o 'Modo Automático' para todos os vídeos do diretório)", variable=self.chain_processing_mode, command=self._toggle_chain_mode).grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="w")

        # --- Botões de Salvar/Carregar Perfil ---
        profile_frame = ctk.CTkFrame(tab)
        profile_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        profile_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(profile_frame, text="Salvar Perfil", command=self._save_preset).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(profile_frame, text="Carregar Perfil", command=self._load_preset).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    def _create_analise_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(tab, text="Prompt Personalizado para Gemini (Opcional):").pack(padx=10, pady=(10,0), anchor="w")
        self.custom_prompt_text_area = ctk.CTkTextbox(tab, wrap="word", height=100)
        self.custom_prompt_text_area.pack(padx=10, pady=5, fill="x", expand=True)

        duration_frame = ctk.CTkFrame(tab)
        duration_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(duration_frame, text="Duração dos Highlights (s):").pack(side="left", padx=10)
        ctk.CTkLabel(duration_frame, text="Min:").pack(side="left")
        ctk.CTkEntry(duration_frame, textvariable=self.min_duration, width=50, validate="key", validatecommand=self.vcmd).pack(side="left", padx=5)
        ctk.CTkLabel(duration_frame, text="Max:").pack(side="left")
        ctk.CTkEntry(duration_frame, textvariable=self.max_duration, width=50, validate="key", validatecommand=self.vcmd).pack(side="left", padx=5)

        advanced_frame = ctk.CTkFrame(tab)
        advanced_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkCheckBox(advanced_frame, text="Análise Vocal de Pitch (Experimental)", variable=self.enable_pitch_analysis).pack(side="left", padx=10)
        ctk.CTkLabel(advanced_frame, text="Idioma da Transcrição:").pack(side="left", padx=10)
        ctk.CTkEntry(advanced_frame, textvariable=self.transcription_language, width=50).pack(side="left", padx=5)

    def _create_legendas_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)

        main_check = ctk.CTkCheckBox(tab, text="Adicionar Legendas ao Vídeo", variable=self.add_subtitles, command=self._toggle_subtitle_options)
        main_check.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")

        self.sub_options_frame = ctk.CTkFrame(tab)
        self.sub_options_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        self.sub_options_frame.grid_columnconfigure(1, weight=1)
        self.sub_options_frame.grid_columnconfigure(3, weight=1)

        # Coluna 0 e 1
        ctk.CTkLabel(self.sub_options_frame, text="Fonte:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkComboBox(self.sub_options_frame, variable=self.subtitle_font, values=["Impact", "Montserrat", "Anton", "Comic Sans MS", "Arial"]).grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.sub_options_frame, text="Tamanho da Fonte:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(self.sub_options_frame, textvariable=self.subtitle_font_size, width=80, validate="key", validatecommand=self.vcmd).grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.sub_options_frame, text="Posição:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkComboBox(self.sub_options_frame, variable=self.subtitle_position, values=["Inferior", "Meio-Inferior", "Centralizado", "Meio-Superior", "Superior"]).grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.sub_options_frame, text="Animação de Ênfase:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkComboBox(self.sub_options_frame, variable=self.subtitle_animation_style, values=["Elastic-Jump"], state="readonly").grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        # Coluna 2 e 3
        ctk.CTkLabel(self.sub_options_frame, text="Tema de Cor:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        ctk.CTkComboBox(self.sub_options_frame, variable=self.subtitle_color_theme, values=["Yellow/White", "Green/White", "Red/White", "Neon Blue/White"]).grid(row=0, column=3, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.sub_options_frame, text="Contorno:").grid(row=1, column=2, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(self.sub_options_frame, textvariable=self.outline_thickness, width=80, validate="key", validatecommand=self.vcmd).grid(row=1, column=3, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.sub_options_frame, text="Sombra:").grid(row=2, column=2, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(self.sub_options_frame, textvariable=self.shadow_depth, width=80, validate="key", validatecommand=self.vcmd).grid(row=2, column=3, padx=10, pady=10, sticky="ew")

        # Checkboxes na parte inferior
        ctk.CTkCheckBox(self.sub_options_frame, text="Sugerir emojis contextuais", variable=self.subtitle_add_emojis).grid(row=4, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkCheckBox(self.sub_options_frame, text="Remover pontuação e deixar minúsculo", variable=self.remove_punctuation).grid(row=4, column=1, padx=10, pady=10, sticky="w")
        
        self._toggle_subtitle_options()

    def _create_audio_export_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)

        # --- Formato de Saída ---
        format_frame = ctk.CTkFrame(tab)
        format_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(format_frame, text="Formato de Saída do Vídeo:").pack(side="left", padx=10)
        ctk.CTkComboBox(format_frame, variable=self.output_format_choice, values=["shorts_vertical", "square"]).pack(side="left", padx=10)

        # --- Música de Fundo ---
        music_frame = ctk.CTkFrame(tab)
        music_frame.pack(pady=10, padx=10, fill="x", expand=True)
        music_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkCheckBox(music_frame, text="Adicionar Música de Fundo", variable=self.add_background_music, command=self._toggle_music_options).grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")

        self.music_options_frame = ctk.CTkFrame(music_frame)
        self.music_options_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        self.music_options_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.music_options_frame, text="Pasta de Músicas:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(self.music_options_frame, textvariable=self.music_folder_path).grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(self.music_options_frame, text="Procurar", command=self._browse_music_folder).grid(row=0, column=2, padx=10, pady=10)

        ctk.CTkLabel(self.music_options_frame, text="Volume da Música (%):").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.volume_slider = ctk.CTkSlider(self.music_options_frame, from_=0, to=100, variable=self.music_volume_percent)
        self.volume_slider.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.volume_label = ctk.CTkLabel(self.music_options_frame, text=f"{self.music_volume_percent.get():.0f}%")
        self.volume_label.grid(row=1, column=2, padx=10, pady=10)
        self.volume_slider.configure(command=lambda value: self.volume_label.configure(text=f"{value:.0f}%"))

        self._toggle_music_options()

    def _save_preset(self):
        preset_name = ctk.CTkInputDialog(text="Digite um nome para o perfil:", title="Salvar Perfil").get_input()
        if not preset_name:
            self._log_message("Operação de salvar perfil cancelada.")
            return

        profiles_dir = "profiles"
        os.makedirs(profiles_dir, exist_ok=True)
        file_path = os.path.join(profiles_dir, f"{preset_name}.json")

        settings = {
            "gemini_api_key": self.gemini_api_key.get(),
            "video_source_path": self.video_source_path.get(),
            "output_base_dir": self.output_base_dir.get(),
            "min_duration": self.min_duration.get(),
            "max_duration": self.max_duration.get(),
            "enable_pitch_analysis": self.enable_pitch_analysis.get(),
            "transcription_language": self.transcription_language.get(),
            "add_subtitles": self.add_subtitles.get(),
            "subtitle_font": self.subtitle_font.get(),
            "subtitle_color_theme": self.subtitle_color_theme.get(),
            "subtitle_animation_style": self.subtitle_animation_style.get(),
            "subtitle_add_emojis": self.subtitle_add_emojis.get(),
            "subtitle_font_size": self.subtitle_font_size.get(),
            "subtitle_position": self.subtitle_position.get(),
            "remove_punctuation": self.remove_punctuation.get(),
            "outline_thickness": self.outline_thickness.get(),
            "shadow_depth": self.shadow_depth.get(),
            "output_format_choice": self.output_format_choice.get(),
            "add_background_music": self.add_background_music.get(),
            "music_folder_path": self.music_folder_path.get(),
            "music_volume_percent": self.music_volume_percent.get(),
            "full_auto_mode": self.full_auto_mode.get(),
            "chain_processing_mode": self.chain_processing_mode.get(),
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
            self._log_message(f"Perfil '{preset_name}' salvo com sucesso em {file_path}")
            messagebox.showinfo("Sucesso", f"Perfil '{preset_name}' salvo com sucesso!")
        except Exception as e:
            self._log_message(f"Erro ao salvar perfil '{preset_name}': {e}")
            messagebox.showerror("Erro", f"Erro ao salvar perfil: {e}")

    def _load_preset(self):
        profiles_dir = "profiles"
        if not os.path.exists(profiles_dir):
            self._log_message("Nenhum perfil salvo encontrado.")
            messagebox.showinfo("Carregar Perfil", "Nenhum perfil salvo encontrado.")
            return

        preset_files = [f for f in os.listdir(profiles_dir) if f.endswith(".json")]
        if not preset_files:
            self._log_message("Nenhum perfil salvo encontrado.")
            messagebox.showinfo("Carregar Perfil", "Nenhum perfil salvo encontrado.")
            return

        # Create a simple dialog to select a preset
        dialog = ctk.CTkToplevel(self)
        dialog.title("Carregar Perfil")
        dialog.geometry("300x200")
        dialog.transient(self) # Make it appear on top of the main window
        dialog.grab_set() # Disable interaction with the main window

        ctk.CTkLabel(dialog, text="Selecione um perfil:").pack(pady=10)

        listbox_frame = ctk.CTkFrame(dialog)
        listbox_frame.pack(padx=10, pady=5, fill="both", expand=True)

        listbox = ctk.CTkScrollableFrame(listbox_frame)
        listbox.pack(fill="both", expand=True)

        selected_preset = ctk.StringVar()

        for preset_file in preset_files:
            preset_name = os.path.splitext(preset_file)[0]
            ctk.CTkRadioButton(listbox, text=preset_name, variable=selected_preset, value=preset_file).pack(anchor="w")

        def on_select():
            file_name = selected_preset.get()
            if not file_name:
                messagebox.showwarning("Carregar Perfil", "Nenhum perfil selecionado.")
                return
            
            file_path = os.path.join(profiles_dir, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                
                # Update application variables
                self.gemini_api_key.set(settings.get("gemini_api_key", ""))
                self.video_source_path.set(settings.get("video_source_path", ""))
                self.output_base_dir.set(settings.get("output_base_dir", ""))
                self.min_duration.set(settings.get("min_duration", "5"))
                self.max_duration.set(settings.get("max_duration", "60"))
                self.enable_pitch_analysis.set(settings.get("enable_pitch_analysis", False))
                self.transcription_language.set(settings.get("transcription_language", "pt"))
                self.add_subtitles.set(settings.get("add_subtitles", True))
                self.subtitle_font.set(settings.get("subtitle_font", "Impact"))
                self.subtitle_color_theme.set(settings.get("subtitle_color_theme", "Yellow/White"))
                self.subtitle_animation_style.set(settings.get("subtitle_animation_style", "Elastic-Jump"))
                self.subtitle_add_emojis.set(settings.get("subtitle_add_emojis", False))
                self.subtitle_font_size.set(settings.get("subtitle_font_size", "70"))
                self.subtitle_position.set(settings.get("subtitle_position", "Inferior"))
                self.remove_punctuation.set(settings.get("remove_punctuation", True))
                self.outline_thickness.set(settings.get("outline_thickness", "4"))
                self.shadow_depth.set(settings.get("shadow_depth", "4"))
                self.output_format_choice.set(settings.get("output_format_choice", "shorts_vertical"))
                self.add_background_music.set(settings.get("add_background_music", False))
                self.music_folder_path.set(settings.get("music_folder_path", ""))
                self.music_volume_percent.set(settings.get("music_volume_percent", 20.0))
                self.full_auto_mode.set(settings.get("full_auto_mode", False))
                self.chain_processing_mode.set(settings.get("chain_processing_mode", False))

                # Update UI elements that depend on these variables
                self._toggle_subtitle_options()
                self._toggle_music_options()
                self._toggle_chain_mode()
                self._toggle_auto_mode()

                self._log_message(f"Perfil '{os.path.splitext(file_name)[0]}' carregado com sucesso.")
                messagebox.showinfo("Sucesso", f"Perfil '{os.path.splitext(file_name)[0]}' carregado com sucesso!")
                dialog.destroy()

            except Exception as e:
                self._log_message(f"Erro ao carregar perfil '{file_name}': {e}")
                messagebox.showerror("Erro", f"Erro ao carregar perfil: {e}")

        ctk.CTkButton(dialog, text="Carregar", command=on_select).pack(pady=10)
        dialog.wait_window(dialog) # Wait for the dialog to close

    def _toggle_subtitle_options(self):
        if not self.add_subtitles.get():
            self.sub_options_frame.grid_remove()
        else:
            self.sub_options_frame.grid()

    def _toggle_music_options(self):
        if not self.add_background_music.get():
            self.music_options_frame.grid_remove()
        else:
            self.music_options_frame.grid()

    def _toggle_chain_mode(self):
        is_chain = self.chain_processing_mode.get()
        if is_chain:
            self.full_auto_mode.set(True)
            self.full_auto_mode_checkbox.configure(state="disabled")
        else:
            self.full_auto_mode_checkbox.configure(state="normal")
        self._toggle_auto_mode()

    def _toggle_auto_mode(self):
        is_auto = self.full_auto_mode.get()
        if is_auto:
            self.process_selected_button.configure(state="disabled")
            self.start_analysis_button.configure(text="Iniciar Processo Automático")
        else:
            if self.chain_processing_mode.get():
                self.full_auto_mode.set(True)
                self._log_message("O 'Modo Automático' é obrigatório para o 'Processamento em Cadeia'.")
                return

            self.start_analysis_button.configure(text="Iniciar Análise")
            if self.highlight_checkboxes:
                self.process_selected_button.configure(state="normal")
            else:
                self.process_selected_button.configure(state="disabled")

    def _browse_video_source(self):
        path = filedialog.askopenfilename(title="Selecione o arquivo de vídeo", filetypes=[("Vídeos", "*.mp4 *.mov *.avi *.mkv")])
        if not path:
            path = filedialog.askdirectory(title="Selecione o diretório com vídeos")
        if path:
            self.video_source_path.set(path)

    def _browse_output_dir(self):
        path = filedialog.askdirectory(title="Selecione o diretório de saída")
        if path:
            self.output_base_dir.set(path)

    def _browse_music_folder(self):
        path = filedialog.askdirectory(title="Selecione a pasta com as músicas de fundo")
        if path:
            self.music_folder_path.set(path)

    def _log_message(self, message):
        def _log():
            if self.winfo_exists(): # Check if the widget still exists
                self.log_text.configure(state="normal")
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        self.after(0, _log)

    def _update_progress(self, value, text):
        def _update():
            if self.winfo_exists(): # Check if the widget still exists
                self.progress_bar.set(value / 100)
                self.progress_label.configure(text=f"Status: {text}")
        self.after(0, _update)

    def _start_analysis_thread(self):
        self.start_analysis_button.configure(state="disabled")
        self.process_selected_button.configure(state="disabled")
        self._log_message("Iniciando análise em segundo plano...")
        self._update_progress(0, "Iniciando análise...")
        
        if self.highlights_main_frame.winfo_exists():
             for widget in self.highlights_main_frame.winfo_children():
                widget.destroy()
        self.highlights_main_frame.pack_forget()
        self.highlights_data = []
        self.highlight_checkboxes = []
        self.current_highlight_video_path = None
        self.current_transcription_path = None

        analysis_thread = threading.Thread(target=self._run_analysis, daemon=True)
        analysis_thread.start()

    def _run_analysis(self):
        video_source = self.video_source_path.get()
        gemini_key = self.gemini_api_key.get()
        
        if not gemini_key:
            self._log_message("Erro: A chave da API Gemini é obrigatória.")
            self.after(0, self._enable_buttons); return
        if not video_source:
            self._log_message("Erro: O vídeo ou diretório de origem é obrigatório.")
            self.after(0, self._enable_buttons); return

        video_files = []
        if os.path.isdir(video_source):
            self._log_message(f"Procurando vídeos no diretório: {video_source}")
            video_files = sorted([os.path.join(video_source, f) for f in os.listdir(video_source) if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))])
        elif os.path.isfile(video_source):
            video_files.append(video_source)

        if not video_files:
            self._log_message("Nenhum arquivo de vídeo válido encontrado.")
            self.after(0, self._enable_buttons); return

        is_chain_processing = self.chain_processing_mode.get() and os.path.isdir(video_source)
        videos_to_process = video_files if is_chain_processing else [video_files[0]]
        total_videos = len(videos_to_process)

        if is_chain_processing and not self.full_auto_mode.get():
            self._log_message("Erro: O Processamento em Cadeia requer que o 'Modo Automático Completo' esteja ativado.")
            self.after(0, self._enable_buttons); return

        for index, video_path in enumerate(videos_to_process):
            self.current_highlight_video_path = video_path
            video_name = os.path.basename(video_path)
            self._log_message(f"--- Iniciando Análise: Vídeo {index + 1}/{total_videos}: {video_name} ---")

            output_dir = "shorts_temp_output"
            os.makedirs(output_dir, exist_ok=True)
            
            # Usar nomes de arquivo temporários únicos para cada vídeo
            base_filename = os.path.splitext(video_name)[0]
            audio_path = os.path.join(output_dir, f"{base_filename}_audio.wav")
            transcription_path = os.path.join(output_dir, f"{base_filename}_transcription.json")
            self.current_transcription_path = transcription_path

            self._update_progress(10, f"Extraindo áudio de {video_name}...")
            if not extract_audio(self.current_highlight_video_path, audio_path, self._log_message):
                self._log_message(f"Falha ao extrair áudio de {video_name}. Pulando para o próximo vídeo.")
                continue

            self._update_progress(30, f"Transcrevendo áudio de {video_name}...")
            if not transcribe_audio(audio_path, transcription_path, self.transcription_language.get(), self._log_message):
                self._log_message(f"Falha ao transcrever áudio de {video_name}. Pulando para o próximo vídeo.")
                continue
            
            try:
                with open(transcription_path, "r", encoding="utf-8") as f:
                    transcription_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                self._log_message(f"Erro ao ler o arquivo de transcrição para {video_name}: {e}. Pulando.")
                continue
            
            transcription_text = " ".join(seg.get('text', '') for seg in transcription_data.get('segments', []))
            if not transcription_text.strip():
                self._log_message(f"Transcrição para {video_name} está vazia. Pulando para o próximo vídeo.")
                continue

            self._update_progress(60, f"Analisando transcrição de {video_name} com Gemini...")
            custom_prompt_input = self.custom_prompt_text_area.get("1.0", "end-1c").strip()
            gemini_prompt_content = custom_prompt_input or "Analise a transcrição e identifique highlights com potencial para shorts. Para cada um, forneça 'start_time', 'end_time', 'title', e um 'score' de 0 a 1000 de potencial de viralização."
            
            try: min_dur = int(self.min_duration.get())
            except (ValueError, TypeError): min_dur = 5
            try: max_dur = int(self.max_duration.get())
            except (ValueError, TypeError): max_dur = 60

            gemini_full_prompt = f'''
            {gemini_prompt_content}
            Duração de cada highlight: entre {min_dur} e {max_dur} segundos.
            Retorne a saída como um array JSON de objetos.
            Exemplo:
            [ {{ "start_time": "00:01:23", "end_time": "00:01:45", "title": "Momento Incrível", "score": 950 }} ]
            Transcrição:
            ---
            {transcription_text}
            ---
            '''
            
            highlights = analyze_transcription_with_gemini(transcription_text, gemini_key, gemini_full_prompt, self._log_message)

            if not highlights:
                self._log_message(f"Análise Gemini falhou ou não retornou highlights para {video_name}.")
                continue

            for h in highlights:
                try:
                    start_s = parse_timestamp_to_seconds(h['start_time'], self._log_message)
                    end_s = parse_timestamp_to_seconds(h['end_time'], self._log_message)
                    h['duration_sec'] = int(end_s - start_s)
                except (KeyError, TypeError):
                    h['duration_sec'] = 0
            
            highlights.sort(key=lambda x: x.get('score', 0), reverse=True)
            self.highlights_data = highlights

            if self.add_subtitles.get():
                self._update_progress(80, f"Estilizando legendas para {video_name}...")
                stylize_transcription(transcription_data, gemini_key, self.subtitle_add_emojis.get(), self._log_message)
                with open(transcription_path, "w", encoding="utf-8") as f:
                    json.dump(transcription_data, f, indent=2, ensure_ascii=False)

            self._update_progress(100, f"Análise de {video_name} completa.")
            
            if self.full_auto_mode.get():
                self._log_message(f"Modo automático: Processando todos os {len(self.highlights_data)} highlights para {video_name}...")
                self._run_processing()
            else:
                self._log_message("Análise completa. Selecione os highlights para processar.")
                self.after(0, self._display_highlights)
                break 

        if is_chain_processing and self.full_auto_mode.get():
            self._log_message("--- Processamento em Cadeia CONCLUÍDO para todos os vídeos. ---")
            if self.winfo_exists():
                self.after(0, lambda: messagebox.showinfo("Concluído", "Processamento em cadeia finalizado com sucesso!"))
        
        self.after(0, self._enable_buttons)

    def _display_highlights(self):
        self.highlights_main_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        ctk.CTkLabel(self.highlights_main_frame, text="Highlights Sugeridos (Ordenados por Score)", font=("", 16, "bold")).pack(pady=(0,10))

        scrollable_frame = ctk.CTkScrollableFrame(self.highlights_main_frame, label_text="")
        scrollable_frame.pack(fill="both", expand=True)

        self.highlight_checkboxes = []
        for highlight in self.highlights_data:
            score = highlight.get('score', 'N/A')
            duration = highlight.get('duration_sec', 'N/A')
            title = highlight.get('title', 'Sem Título')
            
            display_text = f"Score: {score} | Duração: {duration}s - {title}"
            
            var = ctk.BooleanVar(value=True)
            chk = ctk.CTkCheckBox(scrollable_frame, text=display_text, variable=var)
            chk.pack(padx=10, pady=5, fill="x")
            self.highlight_checkboxes.append({"var": var, "data": highlight})
        
        self._enable_buttons()
        if not self.full_auto_mode.get():
            self.process_selected_button.configure(state="normal")

    def _enable_buttons(self):
        if self.winfo_exists():
            self.start_analysis_button.configure(state="normal")
            if not self.full_auto_mode.get() and self.highlight_checkboxes:
                 self.process_selected_button.configure(state="normal")
            else:
                self.process_selected_button.configure(state="disabled")

    def _process_selected_highlights_thread(self):
        self.start_analysis_button.configure(state="disabled")
        self.process_selected_button.configure(state="disabled")
        self._log_message("Processando highlights selecionados...")
        self._update_progress(0, "Iniciando processamento de vídeo...")
        
        processing_thread = threading.Thread(target=self._run_processing, daemon=True)
        processing_thread.start()

    def _run_processing(self):
        if self.full_auto_mode.get():
            selected_highlights = self.highlights_data
        else:
            selected_highlights = [chk["data"] for chk in self.highlight_checkboxes if chk["var"].get()]

        if not selected_highlights:
            self._log_message("Nenhum highlight selecionado.")
            self.after(0, self._enable_buttons); return

        base_output_dir = self.output_base_dir.get()
        os.makedirs(base_output_dir, exist_ok=True)
        
        try: font_size = int(self.subtitle_font_size.get())
        except (ValueError, TypeError): font_size = 70
        try: outline_thickness = int(self.outline_thickness.get())
        except (ValueError, TypeError): outline_thickness = 4
        try: shadow_depth = int(self.shadow_depth.get())
        except (ValueError, TypeError): shadow_depth = 4

        subtitle_options = {
            "add_subtitles": self.add_subtitles.get(),
            "font": self.subtitle_font.get(), "font_size": font_size,
            "position": self.subtitle_position.get(), "color_theme": self.subtitle_color_theme.get(),
            "animation_style": self.subtitle_animation_style.get(), "add_emojis": self.subtitle_add_emojis.get(),
            "remove_punctuation": self.remove_punctuation.get(), "outline_thickness": outline_thickness,
            "shadow_depth": shadow_depth
        }

        music_options = {
            "enabled": self.add_background_music.get(),
            "folder": self.music_folder_path.get(),
            "volume": self.music_volume_percent.get() / 100.0 # Convert percentage to a 0.0-1.0 scale for FFmpeg
        }

        transcription_data = None
        if subtitle_options["add_subtitles"]:
            if not self.current_transcription_path or not os.path.exists(self.current_transcription_path):
                self._log_message(f"Erro: Arquivo de transcrição não encontrado ({self.current_transcription_path}). As legendas não serão adicionadas.")
                subtitle_options["add_subtitles"] = False
            else:
                try:
                    with open(self.current_transcription_path, "r", encoding="utf-8") as f:
                        transcription_data = json.load(f)
                except Exception as e:
                    self._log_message(f"Erro ao carregar transcrição para legendas: {e}")
                    subtitle_options["add_subtitles"] = False

        video_name_no_ext = os.path.splitext(os.path.basename(self.current_highlight_video_path))[0]
        video_specific_output_dir = os.path.join(base_output_dir, video_name_no_ext)
        os.makedirs(video_specific_output_dir, exist_ok=True)

        cut_and_reformat_video(
            original_video_path=self.current_highlight_video_path, 
            highlights_data=selected_highlights, 
            output_dir=video_specific_output_dir, 
            output_format=self.output_format_choice.get(), 
            log_callback=self._log_message, 
            transcription_data=transcription_data,
            subtitle_options=subtitle_options,
            music_options=music_options
        )
        
        if not self.chain_processing_mode.get():
            self._log_message("Processamento Concluído.")
            self._update_progress(100, "Processamento completo.")
            self.after(0, self._enable_buttons)
            

if __name__ == "__main__":
    app = ShortsCreatorApp()
    app.mainloop()