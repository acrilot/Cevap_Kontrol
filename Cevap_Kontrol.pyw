import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import os
import json
import re

DATA_DIR = r"C:\Users\ETHEM\AppData\Local\CevapAnahtariKontrol\data"
os.makedirs(DATA_DIR, exist_ok=True)

class AnswerEvaluator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cevap Değerlendirme")
        self.root.geometry("1200x700")
        
        # Session management variables
        self.current_session_file = None
        self.is_new_session = True
        self.has_changes = False
        self.initial_state = None
        
        self.setup_ui()
        self.update_save_list()
        self.save_initial_state()
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Bind text change events
        self.key_text.bind('<KeyRelease>', self.on_content_change)
        self.answer_text.bind('<KeyRelease>', self.on_content_change)
        self.penalty_entry.bind('<KeyRelease>', self.on_content_change)
        
    def setup_ui(self):
        # Grid configuration
        for i in range(3):
            self.root.grid_columnconfigure(i, weight=1, uniform="group")
        self.root.grid_rowconfigure(1, weight=1)

        # Headers
        font_title = ("Arial", 14, "bold")
        tk.Label(self.root, text="Cevap Anahtarı", font=font_title).grid(row=0, column=0, pady=(10, 0))
        tk.Label(self.root, text="Cevaplarım", font=font_title).grid(row=0, column=1, pady=(10, 0))
        tk.Label(self.root, text="Sonuçlar", font=font_title).grid(row=0, column=2, pady=(10, 0))

        # Text boxes
        self.key_text = tk.Text(self.root, wrap="word", undo=True, maxundo=50)
        self.answer_text = tk.Text(self.root, wrap="word", undo=True, maxundo=50)

        # Create menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dosya", menu=file_menu)
        file_menu.add_command(label="Yeni (Ctrl+N)", command=self.new_file)
        file_menu.add_command(label="Kaydet (Ctrl+S)", command=lambda: self.save_session())
        file_menu.add_command(label="Farklı Kaydet (Ctrl+Shift+S)", command=self.save_to_file)
        file_menu.add_separator()
        file_menu.add_command(label="Listeden Aç", command=self.open_from_list)  # Your original open function
        file_menu.add_command(label="Dosyadan Aç (Ctrl+O)", command=self.open_file)
        file_menu.add_separator()
        file_menu.add_command(label="Çıkış (Ctrl+Q)", command=self.on_closing)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Düzenle", menu=edit_menu)
        edit_menu.add_command(label="Geri Al (Ctrl+Z)", command=self.undo_action)
        edit_menu.add_command(label="Yinele (Ctrl+Y)", command=self.redo_action)
        
        # Add keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_session())
        self.root.bind('<Control-S>', lambda e: self.save_to_file())  # Ctrl+Shift+S
        self.root.bind('<Control-q>', lambda e: self.on_closing())

        # Undo-Redo
        self.key_text.bind('<Control-z>', lambda e: self.key_text.edit_undo())
        self.key_text.bind('<Control-y>', lambda e: self.key_text.edit_redo())
        self.key_text.bind('<Control-Z>', lambda e: self.key_text.edit_redo())  # Ctrl+Shift+Z

        self.answer_text.bind('<Control-z>', lambda e: self.answer_text.edit_undo())
        self.answer_text.bind('<Control-y>', lambda e: self.answer_text.edit_redo())
        self.answer_text.bind('<Control-Z>', lambda e: self.answer_text.edit_redo())  # Ctrl+Shift+Z

        self.key_text.bind("<Button-3>", self.show_context_menu)  # Right click
        self.answer_text.bind("<Button-3>", self.show_context_menu)

        # Right panel (results and save list)
        result_frame = tk.Frame(self.root)
        result_frame.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)
        result_frame.grid_rowconfigure(0, weight=3)
        result_frame.grid_rowconfigure(1, weight=2)
        result_frame.grid_columnconfigure(0, weight=1)

        # Results display (read-only)
        self.result_text = tk.Text(result_frame, wrap="word", bg="#f5f5f5", state="disabled")
        self.result_text.grid(row=0, column=0, sticky="nsew")

        # Save list frame
        save_frame = tk.Frame(result_frame)
        save_frame.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        save_frame.grid_columnconfigure(0, weight=1)
        save_frame.grid_rowconfigure(0, weight=1)

        # Save list with scrollbar
        self.save_listbox = tk.Listbox(save_frame)
        scrollbar = ttk.Scrollbar(save_frame, orient="vertical", command=self.save_listbox.yview)
        self.save_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.save_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Delete button
        ttk.Button(save_frame, text="Seçili Dosyayı Sil", command=self.delete_session).grid(row=1, column=0, columnspan=2, pady=5)
        
        self.save_listbox.bind("<<ListboxSelect>>", self.load_session)

        # Left and center text boxes
        self.key_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.answer_text.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        # Bottom frame
        bottom_frame = tk.Frame(self.root)
        bottom_frame.grid(row=2, column=0, columnspan=3, pady=10)

        tk.Label(bottom_frame, text="Yanlış/Doğru Götürme Oranı:").pack(side="left")
        self.penalty_entry = tk.Entry(bottom_frame, width=5)
        self.penalty_entry.insert(0, "4")
        self.penalty_entry.pack(side="left", padx=5)

        ttk.Button(bottom_frame, text="Hesapla", command=self.calculate).pack(side="left", padx=10)
        ttk.Button(bottom_frame, text="Kaydet", command=self.save_session).pack(side="left", padx=10)

    def undo_action(self):
        try:
            # Get the currently focused widget
            focused = self.root.focus_get()
            if focused in [self.key_text, self.answer_text]:
                focused.edit_undo()
        except:
            pass

    def redo_action(self):
        try:
            # Get the currently focused widget
            focused = self.root.focus_get()
            if focused in [self.key_text, self.answer_text]:
                focused.edit_redo()
        except:
            pass

    def open_from_list(self):
        """Open a save file - same as selecting from the list"""
        files = [f[:-5] for f in os.listdir(DATA_DIR) if f.endswith(".json")]
        if not files:
            messagebox.showinfo("Bilgi", "Açılacak dosya bulunamadı.")
            return
        
        # Create a simple dialog to select file
        dialog = tk.Toplevel(self.root)
        dialog.title("Dosya Aç")
        dialog.geometry("300x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Açmak istediğiniz dosyayı seçin:", font=("Arial", 10, "bold")).pack(pady=10)
        
        # File listbox
        file_listbox = tk.Listbox(dialog)
        file_listbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        for file in sorted(files):
            file_listbox.insert(tk.END, file)
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def on_open():
            selection = file_listbox.curselection()
            if not selection:
                messagebox.showwarning("Uyarı", "Bir dosya seçin.")
                return
            
            name = file_listbox.get(selection[0])
            dialog.destroy()
            
            # Check if we need to save current session
            if self.should_save_before_switch():
                response = messagebox.askyesnocancel("Kayıt", 
                    "Mevcut çalışmanızda değişiklikler var. Kaydetmek istiyor musunuz?")
                if response is True:  # Yes
                    if not self.save_session(auto_save=True):
                        return  # Save failed, don't proceed
                elif response is None:  # Cancel
                    return
            
            # Load the selected file
            filename = os.path.join(DATA_DIR, f"{name}.json")
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.key_text.delete("1.0", tk.END)
                self.key_text.insert(tk.END, data["key"])
                self.answer_text.delete("1.0", tk.END)
                self.answer_text.insert(tk.END, data["user"])
                
                self.result_text.config(state="normal")
                self.result_text.delete("1.0", tk.END)
                self.result_text.insert(tk.END, data["result"])
                self.result_text.config(state="disabled")
                
                self.penalty_entry.delete(0, tk.END)
                self.penalty_entry.insert(0, data.get("penalty", "4"))

                self.current_session_file = name
                self.is_new_session = False
                self.has_changes = False
                self.save_initial_state()
                self.update_title()
                
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya yüklenirken hata oluştu: {str(e)}")
        
        def on_cancel():
            dialog.destroy()
        
        # Double-click to open
        file_listbox.bind("<Double-Button-1>", lambda e: on_open())
        
        ttk.Button(button_frame, text="Aç", command=on_open).pack(side="left", padx=5)
        ttk.Button(button_frame, text="İptal", command=on_cancel).pack(side="left", padx=5)

    def save_to_file(self):
        """Save As - let user choose location and filename"""
        key = self.key_text.get("1.0", tk.END).strip()
        user = self.answer_text.get("1.0", tk.END).strip()
        result = self.result_text.get("1.0", tk.END).strip()
        ratio = self.penalty_entry.get().strip()

        if not key or not user or not result:
            messagebox.showwarning("Uyarı", "Tüm alanlar doldurulmuş olmalı.")
            return

        # Open file dialog for save location
        filename = filedialog.asksaveasfilename(
            title="Farklı Kaydet",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=DATA_DIR,
            initialfile=self.current_session_file if self.current_session_file else "yeni_cevap"
        )
        
        if not filename:
            return  # User cancelled

        data = {
            "key": key,
            "user": user,
            "result": result,
            "penalty": ratio
        }

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Extract just the filename without path and extension for session tracking
            import os
            base_name = os.path.splitext(os.path.basename(filename))[0]
            
            # Only update current session if saved in DATA_DIR
            if os.path.dirname(filename) == os.path.abspath(DATA_DIR):
                self.current_session_file = base_name
                self.is_new_session = False
                self.has_changes = False
                self.save_initial_state()
                self.update_save_list()
                self.update_title()
            else:
                # If saved outside DATA_DIR, don't change session state
                messagebox.showinfo("Bilgi", f"Dosya '{filename}' konumuna kaydedildi.\n\nNot: Bu dosya ana listede görünmeyecek çünkü farklı bir konuma kaydedildi.")
                return
                
            messagebox.showinfo("Başarılı", f"Dosya '{filename}' olarak kaydedildi.")
            
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya kaydedilirken hata oluştu: {str(e)}")

    def open_file(self):
        """Open file - let user choose from file dialog"""
        # Check if we need to save current session first
        if self.should_save_before_switch():
            response = messagebox.askyesnocancel("Kayıt", 
                "Mevcut çalışmanızda değişiklikler var. Kaydetmek istiyor musunuz?")
            if response is True:  # Yes
                if not self.save_session(auto_save=True):
                    return  # Save failed, don't proceed
            elif response is None:  # Cancel
                return
        
        # Open file dialog
        filename = filedialog.askopenfilename(
            title="Dosya Aç",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=DATA_DIR
        )
        
        if not filename:
            return  # User cancelled

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Clear and load data
            self.key_text.delete("1.0", tk.END)
            self.key_text.insert(tk.END, data["key"])
            self.answer_text.delete("1.0", tk.END)
            self.answer_text.insert(tk.END, data["user"])
            
            self.result_text.config(state="normal")
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, data["result"])
            self.result_text.config(state="disabled")
            
            self.penalty_entry.delete(0, tk.END)
            self.penalty_entry.insert(0, data.get("penalty", "4"))

            # Extract filename for session tracking
            import os
            base_name = os.path.splitext(os.path.basename(filename))[0]
            
            # Only track as current session if it's in DATA_DIR
            if os.path.dirname(filename) == os.path.abspath(DATA_DIR):
                self.current_session_file = base_name
                self.is_new_session = False
                self.update_save_list()
            else:
                # If opened from outside DATA_DIR, treat as new session
                self.current_session_file = None
                self.is_new_session = True
                
            self.has_changes = False
            self.save_initial_state()
            self.update_title()
            
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya yüklenirken hata oluştu: {str(e)}")

    def new_file(self):
        """Create a new session"""
        # Check if we need to save current session
        if self.should_save_before_switch():
            response = messagebox.askyesnocancel("Kayıt", 
                "Mevcut çalışmanızda değişiklikler var. Kaydetmek istiyor musunuz?")
            if response is True:  # Yes
                if not self.save_session(auto_save=True):
                    return  # Save failed, don't proceed
            elif response is None:  # Cancel
                return
        
        # Clear all fields
        self.key_text.delete("1.0", tk.END)
        self.answer_text.delete("1.0", tk.END)
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.config(state="disabled")
        self.penalty_entry.delete(0, tk.END)
        self.penalty_entry.insert(0, "4")
        
        # Reset session state
        self.current_session_file = None
        self.is_new_session = True
        self.has_changes = False
        self.save_initial_state()
        self.update_title()
        
        # Clear listbox selection
        self.save_listbox.selection_clear(0, tk.END)

    def show_context_menu(self, event):
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Geri Al", command=lambda: event.widget.edit_undo())
        context_menu.add_command(label="Yinele", command=lambda: event.widget.edit_redo())
        context_menu.add_separator()
        context_menu.add_command(label="Kes", command=lambda: event.widget.event_generate("<<Cut>>"))
        context_menu.add_command(label="Kopyala", command=lambda: event.widget.event_generate("<<Copy>>"))
        context_menu.add_command(label="Yapıştır", command=lambda: event.widget.event_generate("<<Paste>>"))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def parse_answers(self, raw_input):
        answers = {}
        lines = raw_input.strip().split('\n')
        for line in lines:
            match = re.match(r'\s*(\d+)[\.\)]\s*([A-E]?)\s*', line.strip(), re.IGNORECASE)
            if match:
                q_num = int(match.group(1))
                answer = match.group(2).upper()
                answers[q_num] = answer if answer else None
        return answers

    def evaluate(self, key_input, user_input, penalty_ratio):
        key = self.parse_answers(key_input)
        user = self.parse_answers(user_input)

        total = len(key)
        correct = 0
        wrong = 0
        empty = 0
        wrong_details = []
        empty_details = []

        for q_num in range(1, total + 1):
            correct_ans = key.get(q_num)
            user_ans = user.get(q_num)

            if user_ans is None or user_ans == '':
                empty += 1
                empty_details.append(f"{q_num}. ({correct_ans})")
            elif user_ans == correct_ans:
                correct += 1
            else:
                wrong += 1
                wrong_details.append(f"{q_num}. {user_ans} ({correct_ans})")

        net = correct - wrong / penalty_ratio

        result = f"Doğru: {correct}\nYanlış: {wrong}\nBoş: {empty}\nNet: {net:.2f}\n\n"
        if wrong_details:
            result += "Yanlış cevaplar:\n" + '\n'.join(wrong_details) + "\n\n"
        if empty_details:
            result += "Boş bırakılan sorular:\n" + '\n'.join(empty_details) + "\n"

        return result

    def calculate(self):
        key = self.key_text.get("1.0", tk.END)
        user = self.answer_text.get("1.0", tk.END)
        try:
            ratio = float(self.penalty_entry.get())
            result = self.evaluate(key, user, ratio)
            
            # Update results display
            self.result_text.config(state="normal")
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, result)
            self.result_text.config(state="disabled")
            
        except:
            self.result_text.config(state="normal")
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, "Geçerli bir götürme oranı girin.")
            self.result_text.config(state="disabled")

    def get_current_state(self):
        """Get current state of all inputs"""
        return {
            "key": self.key_text.get("1.0", tk.END).strip(),
            "user": self.answer_text.get("1.0", tk.END).strip(),
            "penalty": self.penalty_entry.get().strip()
        }

    def save_initial_state(self):
        """Save initial state for change tracking"""
        self.initial_state = self.get_current_state()

    def on_content_change(self, event=None):
        """Track changes in content"""
        current_state = self.get_current_state()
        self.has_changes = current_state != self.initial_state

    def save_session(self, auto_save=False):
        key = self.key_text.get("1.0", tk.END).strip()
        user = self.answer_text.get("1.0", tk.END).strip()
        result = self.result_text.get("1.0", tk.END).strip()
        ratio = self.penalty_entry.get().strip()

        if not key or not user or not result:
            messagebox.showwarning("Uyarı", "Tüm alanlar doldurulmuş olmalı.")
            return False

        # If auto_save is True and we have a current file, just overwrite it
        if auto_save and self.current_session_file:
            name = self.current_session_file
        else:
            name = simpledialog.askstring("Kayıt İsmi", "Bu karşılaştırmaya ne isim vermek istersiniz?")
            if not name:
                return False

        filename = os.path.join(DATA_DIR, f"{name}.json")
        
        # Only ask for overwrite confirmation if it's a manual save and file exists and it's not the current file
        if not auto_save and os.path.exists(filename) and name != self.current_session_file:
            overwrite = messagebox.askyesno("Üzerine yaz?", f"'{name}' isminde bir kayıt zaten var. Üzerine yazılsın mı?")
            if not overwrite:
                return False

        data = {
            "key": key,
            "user": user,
            "result": result,
            "penalty": ratio
        }

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.current_session_file = name
            self.is_new_session = False
            self.has_changes = False
            self.save_initial_state()
            
            self.update_save_list()
            self.update_title()
            
            if not auto_save:
                messagebox.showinfo("Başarılı", f"Kayıt '{name}' olarak kaydedildi.")
            
            return True
            
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya kaydedilirken hata oluştu: {str(e)}")
            return False

    def update_save_list(self):
        self.save_listbox.delete(0, tk.END)
        files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".json"))
        for file in files:
            self.save_listbox.insert(tk.END, file[:-5])  # .json uzantısı olmadan

    def load_session(self, event):
        selection = self.save_listbox.curselection()
        if not selection:
            return
            
        name = self.save_listbox.get(selection[0])
        
        # Check if we need to save current session
        if self.should_save_before_switch():
            response = messagebox.askyesnocancel("Kayıt", 
                "Mevcut çalışmanızda değişiklikler var. Kaydetmek istiyor musunuz?")
            if response is True:  # Yes
                if not self.save_session(auto_save=True):
                    return  # Save failed, don't proceed
            elif response is None:  # Cancel
                return
        
        filename = os.path.join(DATA_DIR, f"{name}.json")

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.key_text.delete("1.0", tk.END)
            self.key_text.insert(tk.END, data["key"])
            self.answer_text.delete("1.0", tk.END)
            self.answer_text.insert(tk.END, data["user"])
            
            self.result_text.config(state="normal")
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, data["result"])
            self.result_text.config(state="disabled")
            
            self.penalty_entry.delete(0, tk.END)
            self.penalty_entry.insert(0, data.get("penalty", "4"))

            self.current_session_file = name
            self.is_new_session = False
            self.has_changes = False
            self.save_initial_state()
            self.update_title()
            
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya yüklenirken hata oluştu: {str(e)}")

    def delete_session(self):
        selection = self.save_listbox.curselection()
        if not selection:
            messagebox.showwarning("Uyarı", "Silmek için bir dosya seçin.")
            return
            
        name = self.save_listbox.get(selection[0])
        
        # Confirmation dialog
        confirm = messagebox.askyesno("Silme Onayı", 
            f"'{name}' dosyasını silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz.")
        if not confirm:
            return
            
        filename = os.path.join(DATA_DIR, f"{name}.json")
        
        try:
            os.remove(filename)
            self.update_save_list()
            
            # If we deleted the currently open file, reset to new session
            if self.current_session_file == name:
                self.current_session_file = None
                self.is_new_session = True
                self.has_changes = False
                self.save_initial_state()
                self.update_title()
                
            messagebox.showinfo("Başarılı", f"'{name}' dosyası silindi.")
            
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya silinirken hata oluştu: {str(e)}")

    def should_save_before_switch(self):
        """Check if we should ask to save before switching"""
        if not self.has_changes:
            return False
        if self.is_new_session:
            return True
        # If it's from a save file and has changes, also ask
        return self.current_session_file is not None

    def update_title(self):
        """Update window title with current session name"""
        if self.current_session_file:
            self.root.title(f"Cevap Değerlendirme - {self.current_session_file}")
        else:
            self.root.title("Cevap Değerlendirme")

    def on_closing(self):
        """Handle window closing"""
        if self.should_save_before_switch():
            response = messagebox.askyesnocancel("Kayıt", 
                "Mevcut çalışmanızda değişiklikler var. Kaydetmek istiyor musunuz?")
            if response is True:  # Yes
                if not self.save_session(auto_save=True):
                    return  # Save failed, don't proceed
            elif response is None:  # Cancel
                return
        
        self.root.destroy()

    def run(self):
        self.root.mainloop()

# Run the application
if __name__ == "__main__":
    app = AnswerEvaluator()
    app.run()
