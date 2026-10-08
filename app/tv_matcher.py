"""TV Matcher – interfaccia grafica (doppio click) e riga di comando.

Uso da riga di comando:
    python tv_matcher.py --input input.xlsx --paese IT [--visibile]
"""
import argparse
import os
import queue
import sys
import threading

PAESI = ["IT", "DE", "FR", "ES", "UK"]


def cartella_base():
    return os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))


def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from motore import esegui, crea_modello_input

    root = tk.Tk()
    root.title("TV Matcher – confronto Amazon vs retailer")
    root.geometry("760x520")
    q = queue.Queue()
    stato = {"stop": False, "thread": None}

    v_file = tk.StringVar()
    v_paese = tk.StringVar(value="IT")
    v_out = tk.StringVar(value=os.path.join(cartella_base(), "Output"))
    v_vis = tk.BooleanVar(value=False)

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="File di input (Excel):").grid(row=0, column=0, sticky="w")
    ttk.Entry(frm, textvariable=v_file, width=70).grid(row=0, column=1, sticky="we")
    ttk.Button(frm, text="Sfoglia…", command=lambda: v_file.set(
        filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")]) or v_file.get())).grid(row=0, column=2)

    ttk.Label(frm, text="Paese:").grid(row=1, column=0, sticky="w", pady=6)
    ttk.Combobox(frm, textvariable=v_paese, values=PAESI, width=6, state="readonly").grid(row=1, column=1, sticky="w")

    ttk.Label(frm, text="Cartella output:").grid(row=2, column=0, sticky="w")
    ttk.Entry(frm, textvariable=v_out, width=70).grid(row=2, column=1, sticky="we")
    ttk.Button(frm, text="Sfoglia…", command=lambda: v_out.set(
        filedialog.askdirectory() or v_out.get())).grid(row=2, column=2)

    ttk.Checkbutton(frm, text="Mostra il browser durante l'esecuzione (utile se compare un captcha)",
                    variable=v_vis).grid(row=3, column=1, sticky="w", pady=6)

    log = tk.Text(frm, height=18, wrap="word")
    log.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=8)
    frm.rowconfigure(5, weight=1)
    frm.columnconfigure(1, weight=1)

    def nuovo_modello():
        p = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="input_tv_matcher.xlsx")
        if p:
            crea_modello_input(p)
            v_file.set(p)
            messagebox.showinfo("Creato", f"File di input creato:\n{p}\n\nInserisci gli ASIN nel foglio 'ASIN'.")

    def lavoro():
        try:
            out = esegui(v_file.get(), v_paese.get(), v_out.get(), v_vis.get(),
                         log=lambda m: q.put(("log", m)), stop=lambda: stato["stop"])
            q.put(("fine", out))
        except Exception as e:
            q.put(("errore", str(e)))

    def avvia():
        if not os.path.isfile(v_file.get()):
            messagebox.showwarning("Attenzione", "Seleziona un file di input valido.")
            return
        stato["stop"] = False
        b_avvia.config(state="disabled")
        log.delete("1.0", "end")
        stato["thread"] = threading.Thread(target=lavoro, daemon=True)
        stato["thread"].start()

    def ferma():
        stato["stop"] = True
        q.put(("log", "Interruzione richiesta: salvo quanto elaborato…"))

    def poll():
        try:
            while True:
                tipo, msg = q.get_nowait()
                if tipo == "log":
                    log.insert("end", msg + "\n")
                    log.see("end")
                elif tipo == "fine":
                    b_avvia.config(state="normal")
                    log.insert("end", f"\n✔ Completato: {msg}\n")
                    if messagebox.askyesno("Completato", f"Output creato:\n{msg}\n\nAprirlo ora?"):
                        os.startfile(msg) if hasattr(os, "startfile") else None
                elif tipo == "errore":
                    b_avvia.config(state="normal")
                    log.insert("end", f"\n✖ Errore: {msg}\n")
                    messagebox.showerror("Errore", msg)
        except queue.Empty:
            pass
        root.after(300, poll)

    bar = ttk.Frame(frm)
    bar.grid(row=4, column=0, columnspan=3, sticky="w")
    b_avvia = ttk.Button(bar, text="▶ Avvia", command=avvia)
    b_avvia.pack(side="left", padx=4)
    ttk.Button(bar, text="■ Ferma", command=ferma).pack(side="left", padx=4)
    ttk.Button(bar, text="Crea file di input vuoto", command=nuovo_modello).pack(side="left", padx=4)

    poll()
    root.mainloop()


def cli():
    from motore import esegui
    p = argparse.ArgumentParser(description="TV Matcher")
    p.add_argument("--input", required=True)
    p.add_argument("--paese", default="IT", choices=PAESI)
    p.add_argument("--output", default=os.path.join(cartella_base(), "Output"))
    p.add_argument("--visibile", action="store_true")
    a = p.parse_args()
    print("Output:", esegui(a.input, a.paese, a.output, a.visibile))


if __name__ == "__main__":
    cli() if len(sys.argv) > 1 else gui()
