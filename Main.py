from tkinter import *
from tkinter.filedialog import askopenfilename
from hashlib import sha256
import datetime
import json
import os
import pickle
import re
import webbrowser

import qrcode

from Blockchain import Blockchain

BLOCKCHAIN_FILE = 'blockchain_contract.txt'
QR_DIR = 'generated_qr'

main = Tk()
main.title("SecureChain Product Authentication")
main.geometry("1180x760")
main.minsize(1000, 680)

blockchain = Blockchain()
if os.path.exists(BLOCKCHAIN_FILE):
    with open(BLOCKCHAIN_FILE, 'rb') as fileinput:
        try:
            blockchain = pickle.load(fileinput)
        except Exception:
            blockchain = Blockchain()


def sanitize_filename(value):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', value)


def get_file_signature(file_path):
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    return sha256(file_bytes).hexdigest()


def parse_transaction(transaction_data):
    if isinstance(transaction_data, dict):
        return transaction_data

    if isinstance(transaction_data, str) and transaction_data.strip().startswith('{'):
        try:
            parsed = json.loads(transaction_data)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    arr = str(transaction_data).split("#")
    if len(arr) >= 6:
        data = {
            "pid": arr[0],
            "name": arr[1],
            "user": arr[2],
            "address": arr[3],
            "timestamp": arr[4],
            "signature": arr[5],
        }
        if len(arr) >= 7:
            data["qr_path"] = arr[6]
        return data
    return None


def write_report(block_no, details):
    rows = [
        ("Block No", str(block_no)),
        ("Product ID", details.get("pid", "")),
        ("Product Name", details.get("name", "")),
        ("Company/User Details", details.get("user", "")),
        ("Address Details", details.get("address", "")),
        ("Scan Date & Time", details.get("timestamp", "")),
        ("Product Barcode Digital Signature", details.get("signature", "")),
        ("Generated QR Path", details.get("qr_path", "N/A")),
    ]

    output = '<html><body><table border="1" cellspacing="0" cellpadding="8">'
    output += '<tr><th>Field</th><th>Value</th></tr>'
    for key, value in rows:
        output += f'<tr><td>{key}</td><td>{value}</td></tr>'
    output += '</table></body></html>'

    with open("output.html", "w", encoding="utf-8") as f:
        f.write(output)
    webbrowser.open("output.html", new=1)


def print_details_to_console(header, details):
    text.insert(END, header + "\n\n")
    text.insert(END, "Product ID                   : " + details.get("pid", "") + "\n")
    text.insert(END, "Product Name                 : " + details.get("name", "") + "\n")
    text.insert(END, "Company/User Details         : " + details.get("user", "") + "\n")
    text.insert(END, "Address Details              : " + details.get("address", "") + "\n")
    text.insert(END, "Scan Date & Time             : " + details.get("timestamp", "") + "\n")
    text.insert(END, "Product Barcode Digital Sign : " + details.get("signature", "") + "\n")
    text.insert(END, "Generated QR Path            : " + details.get("qr_path", "N/A") + "\n")


def iter_chain_products():
    for i, block in enumerate(blockchain.chain):
        if i == 0:
            continue
        for tx in block.transactions:
            parsed = parse_transaction(tx)
            if parsed:
                yield i, parsed

def addProduct():
    text.delete('1.0', END)
    pid = tf1.get()
    name = tf2.get()
    user = tf3.get()
    address = tf4.get()

    if len(pid) > 0 and len(name) > 0 and len(user) > 0 and len(address) > 0:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs(QR_DIR, exist_ok=True)

        qr_payload = {
            "pid": pid,
            "name": name,
            "user": user,
            "address": address,
            "created_at": current_time,
        }
        safe_name = sanitize_filename(pid)
        qr_file = os.path.join(QR_DIR, f"{safe_name}_{int(datetime.datetime.now().timestamp())}.png")
        qr_img = qrcode.make(json.dumps(qr_payload, sort_keys=True))
        qr_img.save(qr_file)

        digital_signature = get_file_signature(qr_file)
        data = json.dumps({
            "pid": pid,
            "name": name,
            "user": user,
            "address": address,
            "timestamp": current_time,
            "signature": digital_signature,
            "qr_path": qr_file,
        }, sort_keys=True)

        blockchain.add_new_transaction(data)
        blockchain.mine()
        b = blockchain.chain[len(blockchain.chain) - 1]
        text.insert(END,"Blockchain Previous Hash : "+str(b.previous_hash)+"\nBlock No : "+str(b.index)+"\nCurrent Hash : "+str(b.hash)+"\n")
        text.insert(END,"Barcode Blockchain Digital Signature : "+str(digital_signature)+"\n\n")
        text.insert(END, "Generated Product QR Image : " + qr_file + "\n")
        blockchain.save_object(blockchain, BLOCKCHAIN_FILE)
        set_status("Product registered and QR generated", "success")
        update_stats()
        tf1.delete(0, 'end')
        tf2.delete(0, 'end')
        tf3.delete(0, 'end')
        tf4.delete(0, 'end')
    else:
        set_status("Missing product details", "warning")
        text.insert(END,"Please enter all details")

def authenticateProduct():
    text.delete('1.0', END)
    file_path = askopenfilename(initialdir=QR_DIR)
    if not file_path:
        set_status("Authentication cancelled", "warning")
        text.insert(END, "Authentication cancelled. No file selected.")
        return

    digital_signature = get_file_signature(file_path)
    for block_no, details in iter_chain_products():
        if details.get("signature") == digital_signature:
            set_status("Authentic product verified", "success")
            text.insert(END, "Uploaded Product Barcode Authentication Successful\n")
            print_details_to_console("Details extracted from Blockchain after Validation", details)
            write_report(block_no, details)
            return
    set_status("Authentication failed", "danger")
    text.insert(END,"Uploaded Product Barcode Authentication Failed")

def searchProduct():
    text.delete('1.0', END)
    pid = tf1.get().strip()
    if len(pid) > 0:
        for block_no, details in iter_chain_products():
            if details.get("pid") == pid:
                set_status("Product found in ledger", "success")
                print_details_to_console("Product Details extracted from Blockchain using Product ID : " + pid, details)
                write_report(block_no, details)
                return
        set_status("Product not found", "danger")
        text.insert(END,"Given product id does not exists")
    else:
        set_status("Enter product ID to search", "warning")
        text.insert(END, "Please enter product id")
        
    
    

# UI theme colors
BG_ROOT = "#eef2f9"
HEADER_BG = "#0f172a"
SURFACE = "#ffffff"
SURFACE_ALT = "#f8fbff"
TEXT_DARK = "#111827"
TEXT_MUTED = "#64748b"
ACCENT_BLUE = "#0ea5e9"
ACCENT_BLUE_HOVER = "#0284c7"
ACCENT_SLATE = "#1f2937"
ACCENT_SLATE_HOVER = "#111827"
ACCENT_TEAL = "#0f766e"
ACCENT_TEAL_HOVER = "#0d5f58"
SUCCESS_BG = "#dcfce7"
SUCCESS_FG = "#166534"
WARNING_BG = "#fef3c7"
WARNING_FG = "#92400e"
DANGER_BG = "#fee2e2"
DANGER_FG = "#991b1b"
CONSOLE_BG = "#0b1220"
CONSOLE_TEXT = "#d1fae5"


def bind_button_hover(widget, normal_bg, hover_bg):
    def on_enter(_event):
        widget.configure(bg=hover_bg)

    def on_leave(_event):
        widget.configure(bg=normal_bg)

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


def set_status(message, kind="success"):
    if kind == "success":
        status_badge.configure(bg=SUCCESS_BG, fg=SUCCESS_FG)
    elif kind == "warning":
        status_badge.configure(bg=WARNING_BG, fg=WARNING_FG)
    else:
        status_badge.configure(bg=DANGER_BG, fg=DANGER_FG)
    status_badge.configure(text=message)


def update_stats():
    total_blocks = max(len(blockchain.chain) - 1, 0)
    total_products = 0
    for _block_no, _details in iter_chain_products():
        total_products += 1

    blocks_value.configure(text=str(total_blocks))
    products_value.configure(text=str(total_products))


main.configure(bg=BG_ROOT)

# Header
header = Frame(main, bg=HEADER_BG, height=96)
header.pack(fill=X)

header_left = Frame(header, bg=HEADER_BG)
header_left.pack(side=LEFT, padx=24, pady=16)

title = Label(
    header_left,
    text="SecureChain Dashboard",
    bg=HEADER_BG,
    fg="#f1f5f9",
    font=("Segoe UI Semibold", 21)
)
title.pack(anchor="w")

subtitle = Label(
    header_left,
    text="Beautifully simple blockchain verification for premium products",
    bg=HEADER_BG,
    fg="#94a3b8",
    font=("Segoe UI", 10)
)
subtitle.pack(anchor="w", pady=(2, 0))

status_badge = Label(
    header,
    text="System ready",
    bg=SUCCESS_BG,
    fg=SUCCESS_FG,
    font=("Segoe UI Semibold", 10),
    padx=14,
    pady=6
)
status_badge.pack(side=RIGHT, padx=24)

# Main layout
content = Frame(main, bg=BG_ROOT)
content.pack(fill=BOTH, expand=True, padx=24, pady=18)

content.grid_columnconfigure(0, weight=4)
content.grid_columnconfigure(1, weight=3)
content.grid_rowconfigure(1, weight=1)

stats_card = Frame(content, bg=SURFACE, bd=1, relief="solid")
stats_card.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
stats_card.grid_columnconfigure(0, weight=1)
stats_card.grid_columnconfigure(1, weight=1)

blocks_frame = Frame(stats_card, bg=SURFACE)
blocks_frame.grid(row=0, column=0, sticky="w", padx=22, pady=14)
Label(blocks_frame, text="Ledger Blocks", bg=SURFACE, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w")
blocks_value = Label(blocks_frame, text="0", bg=SURFACE, fg=TEXT_DARK, font=("Segoe UI Semibold", 20))
blocks_value.pack(anchor="w")

products_frame = Frame(stats_card, bg=SURFACE)
products_frame.grid(row=0, column=1, sticky="w", padx=22, pady=14)
Label(products_frame, text="Registered Products", bg=SURFACE, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w")
products_value = Label(products_frame, text="0", bg=SURFACE, fg=TEXT_DARK, font=("Segoe UI Semibold", 20))
products_value.pack(anchor="w")

# Left panel: form
form_card = Frame(content, bg=SURFACE, bd=1, relief="solid")
form_card.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
form_card.grid_columnconfigure(1, weight=1)

Label(form_card, text="Product Registration", bg=SURFACE, fg=TEXT_DARK, font=("Segoe UI Semibold", 14)).grid(
    row=0, column=0, columnspan=2, sticky="w", padx=22, pady=(18, 12)
)
Label(form_card, text="Fill details, generate QR, and commit to blockchain", bg=SURFACE, fg=TEXT_MUTED, font=("Segoe UI", 10)).grid(
    row=1, column=0, columnspan=2, sticky="w", padx=22, pady=(0, 10)
)

label_font = ("Segoe UI", 10)
entry_font = ("Segoe UI", 11)

l1 = Label(form_card, text='Product ID', bg=SURFACE, fg=TEXT_MUTED, font=label_font)
l1.grid(row=2, column=0, sticky="w", padx=(22, 12), pady=8)
tf1 = Entry(form_card, font=entry_font, bg=SURFACE_ALT, fg=TEXT_DARK, relief="flat", highlightthickness=1, highlightbackground="#d6e2f1", highlightcolor=ACCENT_BLUE)
tf1.grid(row=2, column=1, sticky="ew", padx=(0, 22), pady=8, ipady=7)

l2 = Label(form_card, text='Product Name', bg=SURFACE, fg=TEXT_MUTED, font=label_font)
l2.grid(row=3, column=0, sticky="w", padx=(22, 12), pady=8)
tf2 = Entry(form_card, font=entry_font, bg=SURFACE_ALT, fg=TEXT_DARK, relief="flat", highlightthickness=1, highlightbackground="#d6e2f1", highlightcolor=ACCENT_BLUE)
tf2.grid(row=3, column=1, sticky="ew", padx=(0, 22), pady=8, ipady=7)

l3 = Label(form_card, text='Company / User', bg=SURFACE, fg=TEXT_MUTED, font=label_font)
l3.grid(row=4, column=0, sticky="w", padx=(22, 12), pady=8)
tf3 = Entry(form_card, font=entry_font, bg=SURFACE_ALT, fg=TEXT_DARK, relief="flat", highlightthickness=1, highlightbackground="#d6e2f1", highlightcolor=ACCENT_BLUE)
tf3.grid(row=4, column=1, sticky="ew", padx=(0, 22), pady=8, ipady=7)

l4 = Label(form_card, text='Address', bg=SURFACE, fg=TEXT_MUTED, font=label_font)
l4.grid(row=5, column=0, sticky="w", padx=(22, 12), pady=8)
tf4 = Entry(form_card, font=entry_font, bg=SURFACE_ALT, fg=TEXT_DARK, relief="flat", highlightthickness=1, highlightbackground="#d6e2f1", highlightcolor=ACCENT_BLUE)
tf4.grid(row=5, column=1, sticky="ew", padx=(0, 22), pady=8, ipady=7)

button_row = Frame(form_card, bg=SURFACE)
button_row.grid(row=6, column=0, columnspan=2, sticky="ew", padx=22, pady=(14, 20))
button_row.grid_columnconfigure(0, weight=1)
button_row.grid_columnconfigure(1, weight=1)
button_row.grid_columnconfigure(2, weight=1)

button_style = {
    "font": ("Segoe UI Semibold", 10),
    "fg": "#ffffff",
    "bd": 0,
    "cursor": "hand2",
    "pady": 10,
}

saveButton = Button(button_row, text="Generate + Save", command=addProduct, bg=ACCENT_BLUE, activebackground=ACCENT_BLUE_HOVER, activeforeground="#ffffff", **button_style)
saveButton.grid(row=0, column=0, sticky="ew", padx=(0, 8))

searchButton = Button(button_row, text="Retrieve Product", command=searchProduct, bg=ACCENT_SLATE, activebackground=ACCENT_SLATE_HOVER, activeforeground="#ffffff", **button_style)
searchButton.grid(row=0, column=1, sticky="ew", padx=4)

scanButton = Button(button_row, text="Authenticate", command=authenticateProduct, bg=ACCENT_TEAL, activebackground=ACCENT_TEAL_HOVER, activeforeground="#ffffff", **button_style)
scanButton.grid(row=0, column=2, sticky="ew", padx=(8, 0))

bind_button_hover(saveButton, ACCENT_BLUE, ACCENT_BLUE_HOVER)
bind_button_hover(searchButton, ACCENT_SLATE, ACCENT_SLATE_HOVER)
bind_button_hover(scanButton, ACCENT_TEAL, ACCENT_TEAL_HOVER)

# Right panel: console
right_panel = Frame(content, bg=SURFACE, bd=1, relief="solid")
right_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
right_panel.grid_rowconfigure(1, weight=1)
right_panel.grid_columnconfigure(0, weight=1)

console_header = Frame(right_panel, bg=SURFACE)
console_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))

Label(console_header, text="System Console", bg=SURFACE, fg=TEXT_DARK, font=("Segoe UI Semibold", 13)).pack(anchor="w")
Label(console_header, text="Live logs for registration, search, and authenticity checks", bg=SURFACE, fg=TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

console_frame = Frame(right_panel, bg=CONSOLE_BG)
console_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
console_frame.grid_rowconfigure(0, weight=1)
console_frame.grid_columnconfigure(0, weight=1)

text = Text(
    console_frame,
    font=("Consolas", 10),
    bg=CONSOLE_BG,
    fg=CONSOLE_TEXT,
    insertbackground=CONSOLE_TEXT,
    relief="flat",
    wrap=WORD,
    padx=12,
    pady=10,
)
text.grid(row=0, column=0, sticky="nsew")

scroll = Scrollbar(console_frame, command=text.yview)
scroll.grid(row=0, column=1, sticky="ns")
text.configure(yscrollcommand=scroll.set)

text.insert(END, "System ready. Add product details and click Generate + Save.\n")
update_stats()
main.mainloop()