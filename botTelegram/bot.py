from pydoc import text
from textwrap import fill
import pytz
import os 
import time
import extract_msg
import vobject
from telegram import Bot, InputFile, ReplyKeyboardRemove, Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram.ext import Updater, ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, PicklePersistence, CallbackContext, ContextTypes
import logging
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import nest_asyncio
import asyncio
import re

nest_asyncio.apply()
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

# Definisikan state untuk conversation
CHOOSING = 1

ALLOWED_USERS_FILE = 'allowed_users.json'

# Load allowed users from JSON file
# Daftar chat_id yang diizinkan
ALLOWED_CHAT_ID = [1188243355]  # Hanya chat_id ini yang diizinkan

def is_user_allowed(update: Update):
    """Memeriksa apakah pengguna memiliki akses dari allowed_users.json."""
    user_id = update.effective_chat.id

    ensure_users_file()  # Pastikan file allowed_users.json ada
    with open(ALLOWED_USERS_FILE, 'r') as f:
        data = json.load(f)

    for user in data['users']:
        if user['id'] == user_id:
            if "temporary" in user['role']:
                # Cek durasi akses untuk pengguna sementara
                duration_days = int(user['role'].split('_')[1])
                added_date = datetime.strptime(user['added_date'], "%Y-%m-%d")
                expiry_date = added_date + timedelta(days=duration_days)
                if datetime.now() > expiry_date:
                    return False  # Akses telah kedaluwarsa
            return True  # Pengguna memiliki akses valid
    return False  # Pengguna tidak ditemukan di daftar
def convert_txt_to_vcf(file_path, vcf_filename, contact_name, partition_size=None, starting_number=1):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            numbers = [line.strip() for line in f if line.strip()]

        # Memastikan nomor diawali dengan "+"
        numbers = [f"+{number}" if not number.startswith('+') else number for number in numbers]

        indonesia_tz = pytz.timezone('Asia/Jakarta')
        current_time = datetime.now(indonesia_tz)
        date_str = current_time.strftime("%d/%m")  # Format tanggal (ubah ke "-" agar tidak bentrok dengan penamaan file)

        vcf_files = []
        os.makedirs('downloads', exist_ok=True)

        # Jika partition_size tidak diberikan atau lebih besar dari jumlah data, set ke jumlah data
        if partition_size is None or partition_size > len(numbers):
            partition_size = len(numbers)

        # Urutan untuk nomor file
        file_number = starting_number

        for i in range(0, len(numbers), partition_size):
            # Membuat nama file untuk setiap bagian sesuai input user
            vcf_file_path = f"downloads/{vcf_filename}_{file_number}.vcf"
            
            with open(vcf_file_path, 'w', encoding='utf-8') as f:
                # Urutan nomor untuk kontak, dimulai dari 0001
                contact_number = 1
                for j in range(i, min(i + partition_size, len(numbers))):
                    f.write("BEGIN:VCARD\n")
                    f.write("VERSION:3.0\n")
                    f.write(f"FN:{date_str}-{contact_name}-{str(contact_number).zfill(4)}\n")  
                    f.write(f"TEL;TYPE=CELL:{numbers[j]}\n")
                    f.write("END:VCARD\n")
                    contact_number += 1  
            
            vcf_files.append(vcf_file_path)
            file_number += 1  # Increment nomor file setelah setiap bagian

        return vcf_files
    except Exception as e:
        print(f"Error in convert_txt_to_vcf: {str(e)}")
        return None


def convert_msg_to_vcf(file_path, adm_number):
    try:
        msg = extract_msg.Message(file_path)
        vcf_file_path = file_path.replace('.msg', '.vcf')
        indonesia_tz = pytz.timezone('Asia/Jakarta')
        current_time = datetime.now(indonesia_tz)
        date_str = current_time.strftime("%d/%m")  # Format tanggal
        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            # Format ADM
            f.write("BEGIN:VCARD\n")
            f.write("VERSION:3.0\n")
            f.write(f"FN:{date_str}-ADMIN-0001\n")  # Format dengan tanggal dan nomor urut
            f.write(f"TEL:{adm_number if adm_number.startswith('+') else '+' + adm_number}\n")
            f.write(f"NOTE:SUBJEK: {msg.subject}\n")
            f.write(f"NOTE:TANGGAL: {msg.date}\n")
            f.write(f"NOTE:ISI:\n{msg.body}\n")
            f.write("END:VCARD\n")


        return vcf_file_path
    except Exception as e:
        print(f"Error dalam konversi MSG ke VCF: {str(e)}")
        return None

def convert_msg_to_adm_navy(file_path, adm_number, navy_number):
    try:
        msg = extract_msg.Message(file_path)
        vcf_file_path = file_path.replace('.msg', '.vcf')
        indonesia_tz = pytz.timezone('Asia/Jakarta')
        current_time = datetime.now(indonesia_tz)
        date_str = current_time.strftime("%d/%m")  # Format tanggal
        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            # Format ADM
            f.write("BEGIN:VCARD\n")
            f.write("VERSION:3.0\n")
            f.write(f"FN:{date_str}-ADMIN-0001\n")  # Format dengan tanggal dan nomor urut
            f.write(f"TEL:{adm_number if adm_number.startswith('+') else '+' + adm_number}\n")
            f.write(f"NOTE:SUBJEK: {msg.subject}\n")
            f.write(f"NOTE:TANGGAL: {msg.date}\n")
            f.write(f"NOTE:ISI:\n{msg.body}\n")
            f.write("END:VCARD\n")

            # Format NAVY
            f.write("BEGIN:VCARD\n")
            f.write("VERSION:3.0\n")
            f.write(f"FN:{date_str}-NAVY-0001\n")  # Format dengan tanggal dan nomor urut
            f.write(f"TEL:{navy_number if navy_number.startswith('+') else '+' + navy_number}\n")
            f.write(f"NOTE:SUBJEK: {msg.subject}\n")
            f.write(f"NOTE:TANGGAL: {msg.date}\n")
            f.write(f"NOTE:ISI:\n{msg.body}\n")
            f.write("END:VCARD\n")

        return vcf_file_path
    except Exception as e:
        print(f"Error dalam konversi MSG ke VCF: {str(e)}")
        return None
def convert_multiple_txt_to_vcf(file_paths, contact_name_pattern, vcf_filename_pattern, starting_number=1):
    try:
        vcf_files = []
        os.makedirs('downloads', exist_ok=True)
        indonesia_tz = pytz.timezone('Asia/Jakarta')
        current_time = datetime.now(indonesia_tz)
        date_str = current_time.strftime("%d/%m")  # Format tanggal
        for index, file_path in enumerate(file_paths):
            with open(file_path, 'r', encoding='utf-8') as f:
                numbers = [line.strip() for line in f if line.strip()]

            # Pastikan nomor memiliki format internasional
            numbers = [f"+{num}" if not num.startswith('+') else num for num in numbers]

            # Format nama kontak dan nama file VCF
            contact_name = f"{contact_name_pattern}"
            vcf_filename = f"{vcf_filename_pattern}_{starting_number + index}.vcf"
            vcf_file_path = f"downloads/{vcf_filename}"

            # Menulis file VCF
            with open(vcf_file_path, 'w', encoding='utf-8') as vcf:
                contact_number = 1
                for i, number in enumerate(numbers):
                    vcf.write("BEGIN:VCARD\n")
                    vcf.write("VERSION:3.0\n")
                    vcf.write(f"FN:{date_str}-{contact_name}-{str(contact_number).zfill(4)}\n")
                    vcf.write(f"TEL;TYPE=CELL:{number}\n")
                    vcf.write("END:VCARD\n")
                    contact_number += 1
            vcf_files.append(vcf_file_path)

        return vcf_files
    except Exception as e:
        return None
# Fungsi untuk menangani pemisahan file


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fungsi start untuk memulai bot."""
    if not is_user_allowed(update):
        await update.message.reply_text("❌ Anda tidak memiliki akses ke bot ini, Silahkan Hubungi @matttt36.")
        return

    # Definisikan keyboard khusus untuk chat ID tertentu
    if update.effective_chat.id == 1188243355:
        keyboard = [
            [KeyboardButton("Start 🔄")],
            [KeyboardButton("PECAH FILE TXT ke BEBERAPA VCF 📱"), KeyboardButton("MSG ke ADM & NAVY 📋")],
            [KeyboardButton("MSG ke VCF 📱"), KeyboardButton("Konversi Banyak File TXT ke VCF 📂")],
            [KeyboardButton("Gabung File TXT"), KeyboardButton("Gabung File VCF")],
            [KeyboardButton("Pisah File TXT"), KeyboardButton("Pisah File VCF")],
            [KeyboardButton("Ganti Nama File TXT"), KeyboardButton("Ganti Nama File VCF")],
            [KeyboardButton("VCF ke TXT"), KeyboardButton("Ganti Nama Kontak")],
            [KeyboardButton("Cek Status Anda")],
            [KeyboardButton("Tambah"), KeyboardButton("Hapus"), KeyboardButton("Lihat")]  # Hanya untuk ID 1188243355
        ]
    else:
        keyboard = [
            [KeyboardButton("Start 🔄")],
            [KeyboardButton("PECAH FILE TXT ke BEBERAPA VCF 📱"), KeyboardButton("MSG ke ADM & NAVY 📋")],
            [KeyboardButton("MSG ke VCF 📱"), KeyboardButton("Konversi Banyak File TXT ke VCF 📂")],
            [KeyboardButton("Gabung File TXT"), KeyboardButton("Gabung File VCF")],
            [KeyboardButton("Pisah File TXT"), KeyboardButton("Pisah File VCF")],
            [KeyboardButton("Ganti Nama File TXT"), KeyboardButton("Ganti Nama File VCF")],
            [KeyboardButton("VCF ke TXT"), KeyboardButton("Ganti Nama Kontak")],
            [KeyboardButton("Cek Status Anda")]
        ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    welcome_message = (
        f"🤖 Halo {username}!\n"
        "Selamat datang di *MATT Bot CV*!\n"
        "Silakan pilih menu yang tersedia 🚀.\n"
        "1. Konversi PECAH FILE TXT ke BEBERAPA FILE VCF \n"
        "2. Konversi MSG ke ADM & NAVY\n"
        "3. Konversi MSG ke VCF\n"
        "4. Konversi Banyak File TXT ke VCF\n"
        "5. Gabung File TXT\n"
        "6. Gabung File VCF\n"
        "7. Pisah File TXT\n"
        "8. Pisah File VCF\n"
        "9. Ganti Nama File TXT\n"
        "10. Ganti Nama File VCF\n"
        "11. Konversi VCF ke TXT\n"
        "12. Ganti Nama Kontak didalam file VCF"
    )
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
    return CHOOSING

async def handle_text(update: Update, context: CallbackContext):
    """Menangani pesan pengguna."""
    if not is_user_allowed(update):
        await update.message.reply_text("❌ Anda tidak memiliki akses ke bot ini, Silahkan Hubungi @matttt36.")
        return

    """Fungsi untuk menangani input teks dari keyboard button"""
    user = update.effective_user
    text = update.message.text
    print(f"Received text: {text}")  # Debugging log
    print(f"User data before handling: {context.user_data}")

    if text in ["Start 🔄", "Cancel"]:
        context.user_data.clear()
        return await start(update, context)
    
    elif text == "PECAH FILE TXT ke BEBERAPA VCF 📱":
        context.user_data.clear()
        context.user_data['waiting_for_vcf_filename'] = True
        await update.message.reply_text(
            "Silakan masukkan nama untuk file VCF.\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return CHOOSING

    elif context.user_data.get('waiting_for_vcf_filename'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Proses dibatalkan.")
            return await start(update, context)

        context.user_data['vcf_filename'] = text
        context.user_data['waiting_for_vcf_filename'] = False
        context.user_data['waiting_for_starting_number'] = True
        await update.message.reply_text(
            "Silakan masukkan nomor urut awal untuk file vcf(misalnya: 21):\n"
           "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return CHOOSING

    elif context.user_data.get('waiting_for_starting_number'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Proses dibatalkan.")
            return await start(update, context)

        # Validasi nomor awal, pastikan itu angka
        starting_number = int(text) if text.isdigit() else 1
        context.user_data['starting_number'] = starting_number
        context.user_data['waiting_for_starting_number'] = False
        context.user_data['waiting_for_partition_size'] = True
        await update.message.reply_text(
            "Silakan masukkan jumlah kontak per file:\n"
            "\n"
            "Tekan 'Enter' untuk tidak membagi file\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄"), KeyboardButton("Enter")]], resize_keyboard=True)
        )
        return CHOOSING


    elif context.user_data.get('waiting_for_partition_size'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Proses dibatalkan.")
            return await start(update, context)

    # Pastikan partition_size valid
        if text.isdigit():
            partition_size = int(text)
        else:
            partition_size = None  # Gunakan None jika input tidak valid atau kosong

        context.user_data['partition_size'] = partition_size
        context.user_data['waiting_for_partition_size'] = False
        context.user_data['waiting_for_contact_name'] = True
        await update.message.reply_text(
            "Silakan masukkan nama kontak:\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return CHOOSING


    elif context.user_data.get('waiting_for_contact_name'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Proses dibatalkan.")
            return await start(update, context)

        context.user_data['contact_name'] = text
        context.user_data['waiting_for_contact_name'] = False
        context.user_data['waiting_for_txt_file'] = True
        await update.message.reply_text(
            "Silakan kirim file TXT yang ingin dikonversi.\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return CHOOSING

    elif text == "MSG ke ADM & NAVY 📋":
        context.user_data.clear()
        context.user_data['waiting_for_adm_number'] = True
        context.user_data['adm_numbers'] = []
        context.user_data['navy_numbers'] = []
        await update.message.reply_text(
            "Masukkan nomor Admin:\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return CHOOSING

    elif context.user_data.get('waiting_for_adm_number'):
        if text.lower() == 'cancel':
            await update.message.reply_text("❌ Proses dibatalkan. Kembali ke menu utama.")
            context.user_data['waiting_for_adm_number'] = False
            return await start(update, context)

        # Pisahkan input berdasarkan baris baru dan tambahkan ke daftar
        numbers = text.strip().split('\n')
        for number in numbers:
            if number.strip():
                # Tambahkan tanda plus (+) jika tidak ada
                if not number.startswith('+'):
                    number = '+' + number.strip()
                context.user_data['adm_numbers'].append(number)

        # Langsung lanjut ke input Navy
        context.user_data['waiting_for_adm_number'] = False
        context.user_data['waiting_for_navy_number'] = True
        await update.message.reply_text(
            "Masukkan nomor Navy:\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return CHOOSING

    elif context.user_data.get('waiting_for_navy_number'):
        if text.lower() == 'cancel':
            await update.message.reply_text("❌ Proses dibatalkan. Kembali ke menu utama.")
            context.user_data['waiting_for_navy_number'] = False
            return await start(update, context)

        # Pisahkan input berdasarkan baris baru dan tambahkan ke daftar
        numbers = text.strip().split('\n')
        for number in numbers:
            if number.strip():
                # Tambahkan tanda plus (+) jika tidak ada
                if not number.startswith('+'):
                    number = '+' + number.strip()
                context.user_data['navy_numbers'].append(number)

        # Langsung proses pembuatan VCF
        adm_numbers = context.user_data['adm_numbers']
        navy_numbers = context.user_data['navy_numbers']

        # Buat file VCF dengan nomor yang diberikan
        vcf_file_path = create_vcf_from_multiple_numbers(adm_numbers, navy_numbers)

        if vcf_file_path:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(vcf_file_path, 'rb'),
                filename="Admin Navy.vcf"
            )
            await update.message.reply_text("File Admin & Navy berhasil dibuat! ✅")
        else:
            await update.message.reply_text('Terjadi kesalahan: File VCF tidak dapat dibuat.')

        # Reset state
        context.user_data['adm_numbers'] = []
        context.user_data['navy_numbers'] = []
        context.user_data['waiting_for_adm_number'] = False
        context.user_data['waiting_for_navy_number'] = False

        # Kembali ke menu utama
        return await start(update, context)
    elif text == "MSG ke VCF 📱":
        context.user_data.clear()
        context.user_data['waiting_for_message_vcf'] = True
        context.user_data['contact_name'] = None
        context.user_data['contact_numbers'] = []  # Reset daftar nomor
        context.user_data['waiting_for_file_name'] = False
        context.user_data['waiting_for_numbers'] = False
        await update.message.reply_text(
            "Silakan masukkan nama kontak untuk VCF.\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return CHOOSING

    elif context.user_data.get('waiting_for_message_vcf'):
        if text.lower() == 'cancel':
            # Reset semua state
            context.user_data['waiting_for_message_vcf'] = False
            context.user_data['contact_name'] = None
            context.user_data['contact_numbers'] = []
            context.user_data['waiting_for_file_name'] = False
            context.user_data['waiting_for_numbers'] = False
            await update.message.reply_text("❌ Proses dibatalkan. Kembali ke menu utama.")
            return await start(update, context)

        if context.user_data['contact_name'] is None:
            # Simpan nama kontak
            context.user_data['contact_name'] = text
            context.user_data['waiting_for_file_name'] = True
            await update.message.reply_text(
                f"Nama kontak '{text}' telah disimpan.\n"
                "Sekarang, silakan kirim nama file untuk VCF (misalnya, 'jojo').\n"
                "\n"
                "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
            )
            return CHOOSING

        elif context.user_data.get('waiting_for_file_name'):
            # Simpan nama file
            context.user_data['file_name'] = text
            context.user_data['waiting_for_numbers'] = True
            context.user_data['waiting_for_file_name'] = False  # Reset untuk memastikan hanya sekali
            await update.message.reply_text(
                f"Nama file '{text}' telah disimpan.\n"
                "Sekarang, silakan kirim nomor kontak (bisa lebih dari satu, pisahkan dengan baris baru).\n"
                "\n"
                "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
            )
            return CHOOSING

        elif context.user_data.get('waiting_for_numbers'):
            # Pisahkan input berdasarkan baris baru dan tambahkan ke daftar
            numbers = text.strip().split('\n')
            for number in numbers:
                if number.strip():
                    # Tambahkan tanda plus (+) jika tidak ada
                    if not number.startswith('+'):
                        number = '+' + number.strip()
                    context.user_data['contact_numbers'].append(number)

            contact_numbers = context.user_data['contact_numbers']

            contact_name = context.user_data['contact_name']
            file_name = context.user_data['file_name']

            # Buat file VCF dengan format yang diminta
            vcf_file_path = create_vcf_from_contacts(contact_name, contact_numbers, file_name)

            if vcf_file_path:
                try:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=open(vcf_file_path, 'rb'),
                        filename=f"{file_name}.vcf"
                    )
                    await update.message.reply_text("File VCF berhasil dibuat! ✅")
                except Exception as e:
                    await update.message.reply_text(f"❌ Terjadi kesalahan saat mengirim file: {str(e)}")
            else:
                await update.message.reply_text("❌ Terjadi kesalahan dalam membuat file VCF.")

            # Reset semua state
            context.user_data['waiting_for_message_vcf'] = False
            context.user_data['contact_name'] = None
            context.user_data['contact_numbers'] = []
            context.user_data['waiting_for_file_name'] = False
            context.user_data['waiting_for_numbers'] = False

            # Kembali ke menu utama
            return await start(update, context)


    # Step 1: Wait for contact name pattern
    elif text == "Konversi Banyak File TXT ke VCF 📂":
        context.user_data.clear()
        context.user_data['waiting_for_contact_name_pattern'] = True
        await update.message.reply_text(
            "Masukkan pola nama kontak untuk file VCF (contoh: Contact):\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_contact_name_pattern'):
        context.user_data['contact_name_pattern'] = text
        context.user_data['waiting_for_contact_name_pattern'] = False
        context.user_data['waiting_for_vcf_filenames'] = True
        await update.message.reply_text(
            "Masukkan pola nama file VCF (contoh: FileVCF):\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_vcf_filenames'):
        context.user_data['vcf_filename_pattern'] = text
        context.user_data['waiting_for_vcf_filenames'] = False
        context.user_data['waiting_for_starting_numbers'] = True
        await update.message.reply_text(
            "Masukkan nomor urut awal untuk file VCF:\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_starting_numbers'):
        try:
            context.user_data['starting_numbers'] = int(text)
            context.user_data['waiting_for_starting_numbers'] = False
            context.user_data['waiting_for_multiple_txt_files'] = True
            context.user_data['uploaded_files'] = []  # Inisialisasi daftar file yang diunggah
            await update.message.reply_text(
                "Silakan unggah semua file TXT dalam satu kali pengiriman:\n"
                "\n"
                "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
            )
            return
        except ValueError:
            await update.message.reply_text("Nomor urut harus berupa angka. Coba lagi:")
        return
    elif text == "Cek Status Anda":
        await check_status(update, context)
        return
    elif text == "Gabung File TXT":
        context.user_data.clear()
        context.user_data['merge_mode_txt'] = True
        context.user_data['uploaded_files'] = []
        context.user_data['waiting_for_merge_filename_txt'] = True

        await update.message.reply_text(
            "Silakan masukkan nama file hasil penggabungan (tanpa ekstensi .txt):\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_merge_filename_txt'):
        merge_filename = text.strip()
        
        if not merge_filename:
            await update.message.reply_text("❌ Nama file tidak boleh kosong. Silakan masukkan nama file gabungan lagi.")
            return

        context.user_data['merge_filename'] = merge_filename
        context.user_data['waiting_for_merge_filename_txt'] = False
        context.user_data['waiting_for_txt_files'] = True

        await update.message.reply_text(
            f"✅ Nama file gabungan disimpan sebagai: {merge_filename}.txt\n"
            "Sekarang unggah semua file TXT yang ingin digabung dalam satu kali pengiriman.\n"
            "\n"
            "Tekan 'Mulai Gabung File TXT' setelah semua file diunggah.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Mulai Gabung File TXT")], [KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('merge_mode_txt') and 'merge_filename' not in context.user_data:
        context.user_data['merge_filename'] = text.strip()
        await update.message.reply_text(
            "Nama file telah disimpan.\n"
            "Silakan lanjutkan dengan mengunggah file atau tekan 'Mulai Gabung File TXT' untuk memproses.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Mulai Gabung File TXT")], [KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return
    elif text == "Mulai Gabung File TXT":
        if not context.user_data.get('waiting_for_txt_files'):
            await update.message.reply_text("❌ Mode penggabungan belum diaktifkan. Silakan mulai ulang dengan memilih menu Gabung File TXT.")
            return

        uploaded_files = context.user_data.get('uploaded_files', [])
        if not uploaded_files:
            await update.message.reply_text("❌ Tidak ada file yang diunggah untuk digabung.")
            return

        print(f"DEBUG: Memulai penggabungan untuk {uploaded_files}")
        await update.message.reply_text("⏳ Menggabungkan file... Harap tunggu.")
        await handle_merge_files_txt(update, context)
        return

    elif text == "Gabung File VCF":
        context.user_data.clear()
        context.user_data['merge_mode_vcf'] = True
        context.user_data['uploaded_files_vcf'] = []
        context.user_data['waiting_for_merge_filename_vcf'] = True

        await update.message.reply_text(
            "Silakan masukkan nama file hasil penggabungan (tanpa ekstensi .vcf):\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_merge_filename_vcf'):
        merge_filename = text.strip()
        
        if not merge_filename or any(c in merge_filename for c in "\\/:*?\"<>|"):
            await update.message.reply_text("❌ Nama file tidak boleh kosong atau mengandung karakter ilegal. Silakan masukkan nama file gabungan lagi.")
            return

        context.user_data['merge_filename_vcf'] = merge_filename
        context.user_data['waiting_for_merge_filename_vcf'] = False
        context.user_data['waiting_for_vcf_files'] = True

        await update.message.reply_text(
            f"✅ Nama file gabungan disimpan sebagai: {merge_filename}.vcf\n"
            "Sekarang unggah semua file VCF yang ingin digabung dalam satu kali pengiriman.\n"
            "\n"
            "Tekan 'Mulai Gabung File vcf' setelah semua file diunggah.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Mulai Gabung File VCF")], [KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif text == "Mulai Gabung File VCF":
        if not context.user_data.get('waiting_for_vcf_files'):
            await update.message.reply_text("❌ Mode penggabungan belum diaktifkan. Silakan mulai ulang dengan memilih menu Gabung File VCF.")
            return

        uploaded_files_vcf = context.user_data.get('uploaded_files_vcf', [])
        if not uploaded_files_vcf:
            await update.message.reply_text("❌ Tidak ada file yang diunggah untuk digabung.")
            return

        print(f"DEBUG: Memulai penggabungan untuk {uploaded_files_vcf}")
        await update.message.reply_text("⏳ Menggabungkan file... Harap tunggu.")
        await handle_merge_files_vcf(update, context)
        return

    elif text == "Pisah File TXT":
        context.user_data.clear()
        context.user_data['split_mode_txt'] = True
        context.user_data['uploaded_file'] = None
        context.user_data['waiting_for_split_filename'] = True

        await update.message.reply_text(
            "Silakan masukkan nama file hasil pemisahan (tanpa ekstensi .txt):\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_split_filename'):
        split_filename = text.strip()

        if not split_filename:
            await update.message.reply_text("❌ Nama file tidak boleh kosong. Silakan masukkan nama file pemisahan lagi.")
            return

        context.user_data['split_filename'] = split_filename
        context.user_data['waiting_for_split_filename'] = False
        context.user_data['waiting_for_split_start_num'] = True

        await update.message.reply_text(
            "Silakan masukkan nomor urut awal untuk hasil pemisahan.\n"
            "Contoh: 21",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_split_start_num'):
        start_num = text.strip()

        if not start_num.isdigit():
            await update.message.reply_text("❌ Nomor urut awal harus berupa angka. Silakan masukkan nomor urut awal.")
            return

        context.user_data['start_num'] = int(start_num)
        context.user_data['waiting_for_split_start_num'] = False
        context.user_data['waiting_for_split_lines'] = True

        await update.message.reply_text(
            "Silakan masukkan jumlah isi per file.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_split_lines'):
        lines_per_file = text.strip()

        if not lines_per_file.isdigit() or not (6 <= int(lines_per_file) <= 15):
            await update.message.reply_text("❌ Masukkan dalam bentuk angka.")
            return

        context.user_data['lines_per_file'] = int(lines_per_file)
        context.user_data['waiting_for_split_lines'] = False
        context.user_data['waiting_for_split_txt_file'] = True

        await update.message.reply_text(
            "Sekarang unggah file TXT yang ingin dipisahkan (hanya satu file).",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_split_txt_file'):
        # Panggil handle_file_txt untuk menangani file yang diunggah
        await handle_file_txt(update, context)
        return

    elif text == "Pisah File VCF":
        context.user_data.clear()
        context.user_data['split_mode_vcf'] = True
        context.user_data['uploaded_file_vcf'] = None
        context.user_data['waiting_for_split_filename_vcf'] = True

        await update.message.reply_text(
            "Silakan masukkan nama file hasil pemisahan (tanpa ekstensi .vcf):\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_split_filename_vcf'):
        split_filename_vcf = text.strip()

        if not split_filename_vcf:
            await update.message.reply_text("❌ Nama file tidak boleh kosong. Silakan masukkan nama file pemisahan lagi.")
            return

        context.user_data['split_filename_vcf'] = split_filename_vcf
        context.user_data['waiting_for_split_filename_vcf'] = False
        context.user_data['waiting_for_split_start_num_vcf'] = True

        await update.message.reply_text(
            "Silakan masukkan nomor urut awal untuk hasil pemisahan.\n"
            "Contoh: 21",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_split_start_num_vcf'):
        start_num_vcf = text.strip()

        if not start_num_vcf.isdigit():
            await update.message.reply_text("❌ Nomor urut awal harus berupa angka. Silakan masukkan nomor urut awal.")
            return

        context.user_data['start_num_vcf'] = int(start_num_vcf)
        context.user_data['waiting_for_split_start_num_vcf'] = False
        context.user_data['waiting_for_split_contacts_vcf'] = True

        await update.message.reply_text(
            "Silakan masukkan jumlah kontak per file.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_split_contacts_vcf'):
        contacts_per_file = text.strip()

        if not contacts_per_file.isdigit() or int(contacts_per_file) <= 0:
            await update.message.reply_text("❌ Masukkan dalam bentuk angka yang valid.")
            return

        context.user_data['contacts_per_file_vcf'] = int(contacts_per_file)
        context.user_data['waiting_for_split_contacts_vcf'] = False
        context.user_data['waiting_for_split_vcf_file'] = True

        await update.message.reply_text(
            "Sekarang unggah file VCF yang ingin dipisahkan (hanya satu file).",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_split_vcf_file'):
        # Panggil handle_file_vcf untuk menangani file yang diunggah
        await handle_file_vcf(update, context)
        return

    elif text == "Ganti Nama File TXT":
        context.user_data.clear()
        context.user_data['rename_mode_txt'] = True
        context.user_data['uploaded_files'] = []
        context.user_data['waiting_for_new_filename'] = True

        await update.message.reply_text(
            "Silakan masukkan nama file baru (tanpa ekstensi .txt):\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_new_filename'):
        new_filename = text.strip()

        if not new_filename:
            await update.message.reply_text("❌ Nama file tidak boleh kosong. Silakan masukkan nama file baru lagi.")
            return

        context.user_data['new_filename'] = new_filename
        context.user_data['waiting_for_new_filename'] = False
        context.user_data['waiting_for_start_num'] = True

        await update.message.reply_text(
            "Silakan masukkan nomor urut awal untuk file yang diganti namanya.\n"
            "Contoh: 21",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_start_num'):
        start_num = text.strip()

        if not start_num.isdigit():
            await update.message.reply_text("❌ Nomor urut awal harus berupa angka. Silakan masukkan nomor urut awal.")
            return

        context.user_data['start_num'] = int(start_num)
        context.user_data['waiting_for_start_num'] = False
        context.user_data['waiting_for_rename_txt_files'] = True

        await update.message.reply_text(
            "Silakan unggah semua file TXT yang ingin diganti namanya dalam satu kali pengiriman.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return
    elif text == "Mulai Ganti Nama File TXT":
        if not context.user_data.get('waiting_for_rename_txt_files'):
            await update.message.reply_text("❌ Mode ganti nama belum diaktifkan. Silakan mulai ulang dengan memilih menu Ganti Nama File TXT.")
            return

        uploaded_files = context.user_data.get('uploaded_files', [])
        if not uploaded_files:
            await update.message.reply_text("❌ Tidak ada file yang diunggah untuk diganti namanya.")
            return

        await update.message.reply_text("⏳ Mengganti nama file... Harap tunggu.")
        await process_rename_txt_files(update, context)
        return   
    elif text == "Ganti Nama File VCF":
        context.user_data.clear()
        context.user_data['rename_mode_vcf'] = True
        context.user_data['uploaded_files_vcf'] = []
        context.user_data['waiting_for_new_filename_vcf'] = True

        await update.message.reply_text(
            "Silakan masukkan nama file baru (tanpa ekstensi .vcf):\n"
            "\n"
            "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_new_filename_vcf'):
        new_filename = text.strip()

        if not new_filename:
            await update.message.reply_text("❌ Nama file tidak boleh kosong. Silakan masukkan nama file baru lagi.")
            return

        context.user_data['new_filename_vcf'] = new_filename
        context.user_data['waiting_for_new_filename_vcf'] = False
        context.user_data['waiting_for_start_num_vcf'] = True

        await update.message.reply_text(
            "Silakan masukkan nomor urut awal untuk file yang diganti namanya.\n"
            "Contoh: 21",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_start_num_vcf'):
        start_num = text.strip()

        if not start_num.isdigit():
            await update.message.reply_text("❌ Nomor urut awal harus berupa angka. Silakan masukkan nomor urut awal.")
            return

        context.user_data['start_num_vcf'] = int(start_num)
        context.user_data['waiting_for_start_num_vcf'] = False
        context.user_data['waiting_for_vcf_files'] = True

        await update.message.reply_text(
            "Silakan unggah semua file VCF yang ingin diganti namanya dalam satu kali pengiriman.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return
    elif text == "Mulai Ganti Nama File VCF":
        if not context.user_data.get('waiting_for_vcf_files'):
            await update.message.reply_text("❌ Mode ganti nama belum diaktifkan. Silakan mulai ulang dengan memilih menu Ganti Nama File VCF.")
            return

        uploaded_files_vcf = context.user_data.get('uploaded_files_vcf', [])
        if not uploaded_files_vcf:
            await update.message.reply_text("❌ Tidak ada file yang diunggah untuk diganti namanya.")
            return

        await update.message.reply_text("⏳ Mengganti nama file... Harap tunggu.")
        await process_rename_vcf_files(update, context)
        return

    elif text == "Tambah":
        # Pastikan hanya admin dengan ID tertentu yang dapat mengakses
        if update.effective_user.id != 1188243355:
            await update.message.reply_text("\u274C Anda tidak memiliki izin untuk menggunakan perintah ini.")
            return
        context.user_data.clear()  # Pastikan user_data bersih sebelum mulai
        context.user_data['waiting_for_user_id'] = True
        await update.message.reply_text(
            "Masukkan ID pengguna baru yang ingin ditambahkan:\n\n"
            "Tekan 'Start 🔄' untuk membatalkan.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
        return

    elif context.user_data.get('waiting_for_user_id'):
        try:
            new_user_id = int(text)  # Pastikan input berupa angka
            user_data = await context.bot.get_chat(new_user_id)
            username = user_data.username if user_data.username else "(Tidak ada username)"

            # Simpan data pengguna baru di user_data
            context.user_data['new_user_id'] = new_user_id
            context.user_data['new_username'] = username

            await update.message.reply_text(
                f"Konfirmasi penambahan pengguna baru:\n\n"
                f"ID: {new_user_id}\n"
                f"Username: @{username}\n\n"
                "Silakan pilih durasi akses:",
                reply_markup=ReplyKeyboardMarkup(
                    [["7 hari", "30 hari", "Permanen"], ["Start 🔄"]],
                    resize_keyboard=True
                )
            )

            # Perbarui state ke `waiting_for_duration`
            context.user_data['waiting_for_duration'] = True
            context.user_data['waiting_for_user_id'] = False
        except ValueError:
            await update.message.reply_text(
                "\u274C ID pengguna harus berupa angka. Silakan coba lagi."
            )
        except Exception as e:
            await update.message.reply_text(
                f"\u274C Terjadi kesalahan: {str(e)}"
            )
        return  # Tetap di alur hingga durasi dipilih

    elif context.user_data.get('waiting_for_duration'):
        duration = text
        if duration not in ["7 hari", "30 hari", "Permanen"]:
            await update.message.reply_text(
                "\u274C Pilihan tidak valid. Silakan pilih durasi akses:",
                reply_markup=ReplyKeyboardMarkup(
                    [["7 hari", "30 hari", "Permanen"], ["Start 🔄"]],
                    resize_keyboard=True
                )
            )
            return

        new_user_id = context.user_data.get('new_user_id')
        username = context.user_data.get('new_username')
        role = "permanent" if duration == "Permanen" else f"temporary_{duration.split(' ')[0]}"

        try:
            ensure_users_file()

            with open('allowed_users.json', 'r') as f:
                data = json.load(f)

            if not any(user['id'] == new_user_id for user in data['users']):
                new_user = {
                    "id": new_user_id,
                    "username": username,
                    "role": role,
                    "added_date": datetime.now().strftime("%Y-%m-%d")
                }
                data['users'].append(new_user)

                with open('allowed_users.json', 'w') as f:
                    json.dump(data, f, indent=4)

                await update.message.reply_text(
                    f"\u2705 Pengguna dengan ID {new_user_id} dan username {username} telah ditambahkan dengan durasi {duration}."
                )
            else:
                await update.message.reply_text(
                    f"\u274C Pengguna dengan ID {new_user_id} sudah ada dalam daftar."
                )
        except Exception as e:
            await update.message.reply_text(
                f"\u274C Terjadi kesalahan: {str(e)}"
            )

        # Reset state setelah proses selesai
        context.user_data.clear()
        return  # Keluar setelah durasi diproses


    elif text == "Hapus":
        # Pastikan hanya admin dengan ID tertentu yang dapat mengakses
        if update.effective_user.id != 1188243355:
            await update.message.reply_text("\u274C Anda tidak memiliki izin untuk menggunakan perintah ini.")
            return
        context.user_data.clear()  # Bersihkan state sebelumnya
        context.user_data['waiting_for_user_id_to_remove'] = True  # Set state untuk menunggu input ID pengguna
        try:
            with open('allowed_users.json', 'r') as f:
                data = json.load(f)

            if not data['users']:
                await update.message.reply_text("ℹ️ Tidak ada pengguna terdaftar.")
                return

            # Tampilkan daftar pengguna
            user_list = "📋 Daftar Pengguna:\n\n"
            current_date = datetime.now()
            for user in data['users']:
                # Periksa role pengguna dan hitung sisa durasi jika ada
                role = user.get('role', 'Tidak diketahui')
                if "temporary" in role:
                    duration_days = int(role.split('_')[1])
                    added_date = datetime.strptime(user['added_date'], "%Y-%m-%d")
                    expiry_date = added_date + timedelta(days=duration_days)
                    remaining_days = (expiry_date - current_date).days
                    duration = f"{remaining_days} hari" if remaining_days > 0 else "Kedaluwarsa"
                else:
                    duration = "Permanen"

                user_list += (
                    f"ID: {user['id']}\n"
                    f"Username: @{user['username']}\n"
                    f"Sisa Durasi: {duration}\n"
                    "-------------------\n"
                )

            await update.message.reply_text(
                f"{user_list}\nSilakan masukkan ID pengguna yang ingin dihapus:\n\n"
                "Tekan 'Start 🔄' untuk membatalkan.",
                reply_markup=ReplyKeyboardMarkup([["Start 🔄"]], resize_keyboard=True)
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)}")
        return

    elif context.user_data.get('waiting_for_user_id_to_remove'):
        try:
            # Validasi input ID pengguna
            user_to_remove_id = int(text)
            with open('allowed_users.json', 'r') as f:
                data = json.load(f)

            # Cari pengguna berdasarkan ID
            user_to_remove = next((user for user in data['users'] if user['id'] == user_to_remove_id), None)
            if not user_to_remove:
                await update.message.reply_text(f"❌ Pengguna dengan ID {user_to_remove_id} tidak ditemukan.")
                return

            # Simpan data pengguna untuk konfirmasi
            context.user_data['user_to_remove'] = user_to_remove

            # Tampilkan konfirmasi
            await update.message.reply_text(
                f"Konfirmasi penghapusan pengguna:\n\n"
                f"ID: {user_to_remove['id']}\n"
                f"Username: @{user_to_remove['username']}\n\n"
                "Tekan 'Konfirmasi' untuk menghapus atau 'Start 🔄' untuk membatalkan.",
                reply_markup=ReplyKeyboardMarkup([["Konfirmasi", "Start 🔄"]], resize_keyboard=True)
            )

            # Perbarui state untuk menunggu konfirmasi
            context.user_data['confirm_removal'] = True
            context.user_data['waiting_for_user_id_to_remove'] = False

        except ValueError:
            await update.message.reply_text("❌ ID pengguna harus berupa angka. Silakan coba lagi.")
        except Exception as e:
            await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)}")
        return

    elif context.user_data.get('confirm_removal'):
        if text == "Konfirmasi":
            try:
                user_to_remove = context.user_data.get('user_to_remove')
                with open('allowed_users.json', 'r') as f:
                    data = json.load(f)

                # Hapus pengguna dari daftar
                data['users'] = [user for user in data['users'] if user['id'] != user_to_remove['id']]

                with open('allowed_users.json', 'w') as f:
                    json.dump(data, f, indent=4)

                await update.message.reply_text(
                    f"✅ Pengguna dengan ID {user_to_remove['id']} dan username @{user_to_remove['username']} telah dihapus."
                )

            except Exception as e:
                await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)}")

            # Bersihkan state setelah proses selesai
            context.user_data.clear()

        elif text == "Start 🔄":
            # Batalkan proses penghapusan
            context.user_data.clear()
            await update.message.reply_text(
                "❌ Proses penghapusan dibatalkan.",
                reply_markup=ReplyKeyboardMarkup([["Start 🔄"]], resize_keyboard=True)
            )

        return

    elif text == "Lihat":
        # Pastikan hanya admin dengan ID tertentu yang dapat mengakses
        if update.effective_user.id != 1188243355:
            await update.message.reply_text("\u274C Anda tidak memiliki izin untuk menggunakan perintah ini.")
            return
        await list_users(update, context)
        return CHOOSING

    # Jika tidak ada kondisi yang terpenuhi
    await update.message.reply_text(
                "Tidak Ada Menu Yang Anda Pilih\n"
                "Tekan 'Start 🔄' Untuk Ulang atau Memulai Kembali",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )
    return CHOOSING

async def send_vcf_files(update, vcf_files):
        # Assuming you want to send the VCF files as a zip or as individual files
    for vcf_file_path in vcf_files:
        with open(vcf_file_path, 'rb') as vcf_file:
            await update.message.reply_document(InputFile(vcf_file, filename=vcf_file_path))
            # Optionally, clean up after sending
        os.remove(vcf_file_path)
def create_vcf_from_multiple_numbers(adm_numbers, navy_numbers):
    """Fungsi untuk membuat VCF dari nomor Admin dan Navy"""
    try:
        vcf_file_path = "downloads/AdminNavy.vcf"
        os.makedirs('downloads', exist_ok=True)

        # Ambil tanggal saat ini (format Indonesia)
        current_date = datetime.now().strftime("%d/%m")

        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            # Tulis nomor Admin
            for i, number in enumerate(adm_numbers, 1):
                f.write("BEGIN:VCARD\n")
                f.write("VERSION:3.0\n")
                f.write(f"FN:{current_date}-ADMIN-{i:04d}\n")
                f.write(f"TEL;TYPE=CELL:{number}\n")
                f.write("END:VCARD\n")

            # Tulis nomor Navy
            for i, number in enumerate(navy_numbers, 1):
                f.write("BEGIN:VCARD\n")
                f.write("VERSION:3.0\n")
                f.write(f"FN:{current_date}-NAVY-{i:04d}\n")
                f.write(f"TEL;TYPE=CELL:{number}\n")
                f.write("END:VCARD\n")

        return vcf_file_path
    except Exception as e:
        return None
def create_vcf_from_contacts(base_name, contact_numbers, file_name):
    """Fungsi untuk membuat VCF dari daftar kontak"""
    try:
        vcf_file_path = f"downloads/{file_name}.vcf"
        os.makedirs('downloads', exist_ok=True)

        # Ambil tanggal saat ini dalam format Indonesia
        current_date = datetime.now().strftime("%d/%m")

        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            for i, number in enumerate(contact_numbers, 1):
                formatted_name = f"{current_date}-{base_name}-{i:04d}"
                f.write("BEGIN:VCARD\n")
                f.write("VERSION:3.0\n")
                f.write(f"FN:{formatted_name}\n")
                f.write(f"TEL;TYPE=CELL:{number}\n")
                f.write("END:VCARD\n")

        return vcf_file_path
    except Exception as e:
        return None
async def handle_file_txt(update: Update, context: CallbackContext):
    """Fungsi untuk menangani file TXT yang dikirim user dan mengonversinya ke VCF."""
    try:
        file_txt = await update.message.document.get_file()
        file_name = update.message.document.file_name

        if not file_name:
            await update.message.reply_text("❌ File tidak memiliki nama. Pastikan file memiliki nama yang valid.")
            return

        if not file_name.lower().endswith('.txt'):
            await update.message.reply_text("❌ Hanya file TXT yang dapat diterima.")
            return

        downloaded_file = f"downloads/{file_name}"
        os.makedirs('downloads', exist_ok=True)
        await file_txt.download_to_drive(downloaded_file)
        print(f"File {file_name} berhasil diunduh ke {downloaded_file}.")

        # **1️⃣ Mode unggah satu file TXT**
        if context.user_data.get('waiting_for_txt_file'):
            vcf_filename = context.user_data.get('vcf_filename', 'contacts')
            contact_name = context.user_data.get('contact_name', 'Contact')
            partition_size = context.user_data.get('partition_size')
            starting_number = context.user_data.get('starting_number', 1)

            print(f"🔄 Konversi dimulai: vcf_filename={vcf_filename}, contact_name={contact_name}, "
                  f"partition_size={partition_size}, starting_number={starting_number}")

            vcf_files = convert_txt_to_vcf(downloaded_file, vcf_filename, contact_name, partition_size, starting_number)

            if vcf_files:
                for vcf_file in vcf_files:
                    with open(vcf_file, 'rb') as doc:
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=doc,
                            filename=os.path.basename(vcf_file)
                        )
                        print(f"✅ File {vcf_file} berhasil dikirim ke user.")

                    if os.path.exists(vcf_file):
                        os.remove(vcf_file)
                        print(f"🗑️ File {vcf_file} telah dihapus.")

                await update.message.reply_text("✅ Semua file VCF berhasil dibuat dan dikirim!")

            else:
                await update.message.reply_text("❌ Terjadi kesalahan saat mengonversi file.")

            # Hapus file TXT setelah diproses
            if os.path.exists(downloaded_file):
                os.remove(downloaded_file)
                print(f"🗑️ File sementara {downloaded_file} telah dihapus.")

            # Reset state setelah proses selesai
            context.user_data.clear()
            return

        # **2️⃣ Mode unggah banyak file TXT (batch)**
        if context.user_data.get('waiting_for_multiple_txt_files'):
            uploaded_files = context.user_data.get("uploaded_files", [])
            uploaded_files.append(downloaded_file)
            context.user_data["uploaded_files"] = uploaded_files
            context.user_data['chat_id'] = update.effective_chat.id
            print(f"📥 File {file_name} berhasil diunggah dan disimpan sementara.")

            # Mulai timer untuk deteksi akhir pengunggahan
            if not context.user_data.get('timer_running', False):
                context.user_data['timer_running'] = True
                asyncio.create_task(start_conversion_timer(context))

            return
        if context.user_data.get('merge_mode_txt'):  # Jika sedang dalam mode penggabungan file
            uploaded_files = context.user_data.get('uploaded_files', [])
            uploaded_files.append(downloaded_file)
            context.user_data['uploaded_files'] = uploaded_files
            print(f"📥 DEBUG: Files uploaded so far: {uploaded_files}")

            await update.message.reply_text(f"📥 File {file_name} berhasil diunggah. Kirimkan file lainnya atau tekan 'Mulai Gabung File TXT' jika sudah selesai.")
            return

        # Jika bukan dalam mode penggabungan, lanjutkan proses pemisahan file (misalnya split)
        if context.user_data.get('waiting_for_split_txt_file'):  # Jika sedang dalam mode pemisahan file
            context.user_data['uploaded_file'] = downloaded_file  # Simpan file yang diupload untuk diproses lebih lanjut
            await update.message.reply_text(f"📥 File {file_name} berhasil diunggah untuk dipisah. Sekarang memulai pemisahan file.")
            await process_split_txt(update, context)  # Panggil fungsi untuk memisahkan file
            return
        elif context.user_data.get('waiting_for_rename_txt_files'):
            # Menangani file yang diunggah oleh pengguna
            await handle_uploaded_txt_files(update, context)
            return
        
        
    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)}")
        print(f"🚨 Error: {str(e)}")
async def handle_uploaded_txt_files(update: Update, context: CallbackContext):
    """Fungsi untuk menangani file TXT yang diunggah user."""
    try:
        file = await update.message.document.get_file()
        file_name = update.message.document.file_name

        if not file_name:
            await update.message.reply_text("❌ File tidak memiliki nama. Pastikan file memiliki nama yang valid.")
            return

        if not file_name.lower().endswith('.txt'):
            await update.message.reply_text("❌ Hanya file TXT yang dapat diterima.")
            return

        downloaded_file = f"downloads/{file_name}"
        os.makedirs('downloads', exist_ok=True)
        await file.download_to_drive(downloaded_file)
        print(f"📥 File {file_name} berhasil diunduh ke {downloaded_file}.")

        uploaded_files = context.user_data.get('uploaded_files', [])
        uploaded_files.append(downloaded_file)
        context.user_data['uploaded_files'] = uploaded_files

        await update.message.reply_text(
            f"📥 File {file_name} berhasil diunggah. Kirimkan file lainnya atau tekan 'Mulai Ganti Nama File TXT' jika sudah selesai.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Mulai Ganti Nama File TXT")], [KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan saat mengunggah file: {str(e)}")
        print(f"🚨 Error: {str(e)}")
async def process_rename_txt_files(update: Update, context: CallbackContext):
    """Mengganti nama file TXT yang telah diunggah sesuai dengan format yang diminta."""
    try:
        uploaded_files = context.user_data.get('uploaded_files', [])
        if not uploaded_files:
            await update.message.reply_text("❌ Tidak ada file yang diunggah untuk diganti namanya.")
            return

        new_filename = context.user_data.get('new_filename')
        start_num = context.user_data.get('start_num')

        renamed_files = []
        file_counter = start_num

        for file_path in uploaded_files:
            renamed_file_path = f"downloads/{new_filename}_{file_counter}.txt"
            os.rename(file_path, renamed_file_path)
            renamed_files.append(renamed_file_path)
            file_counter += 1

        # Kirim file yang telah diganti namanya
        for renamed_file in renamed_files:
            with open(renamed_file, 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=os.path.basename(renamed_file)
                )

        # Hapus file yang telah dikirim
        for renamed_file in renamed_files:
            if os.path.exists(renamed_file):
                os.remove(renamed_file)

        await update.message.reply_text("✅ Semua file berhasil diganti namanya dan dikirim!")

        # Reset state setelah selesai
        context.user_data.clear()

    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan saat mengganti nama file: {str(e)}")
        print(f"🚨 Error: {str(e)}")
async def handle_uploaded_vcf_files(update: Update, context: CallbackContext):
    """Fungsi untuk menangani file VCF yang diunggah user."""
    try:
        file = await update.message.document.get_file()
        file_name = update.message.document.file_name

        if not file_name:
            await update.message.reply_text("❌ File tidak memiliki nama. Pastikan file memiliki nama yang valid.")
            return

        if not file_name.lower().endswith('.vcf'):
            await update.message.reply_text("❌ Hanya file VCF yang dapat diterima.")
            return

        downloaded_file = f"downloads/{file_name}"
        os.makedirs('downloads', exist_ok=True)
        await file.download_to_drive(downloaded_file)
        print(f"📥 File {file_name} berhasil diunduh ke {downloaded_file}.")

        uploaded_files_vcf = context.user_data.get('uploaded_files_vcf', [])
        uploaded_files_vcf.append(downloaded_file)
        context.user_data['uploaded_files_vcf'] = uploaded_files_vcf

        await update.message.reply_text(
            f"📥 File {file_name} berhasil diunggah. Kirimkan file lainnya atau tekan 'Mulai Ganti Nama File VCF' jika sudah selesai.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Mulai Ganti Nama File VCF")], [KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan saat mengunggah file: {str(e)}")
        print(f"🚨 Error: {str(e)}")  
 
async def process_rename_vcf_files(update: Update, context: CallbackContext):
    """Mengganti nama file VCF yang telah diunggah sesuai dengan format yang diminta."""
    try:
        uploaded_files_vcf = context.user_data.get('uploaded_files_vcf', [])
        if not uploaded_files_vcf:
            await update.message.reply_text("❌ Tidak ada file yang diunggah untuk diganti namanya.")
            return

        new_filename_vcf = context.user_data.get('new_filename_vcf')
        start_num_vcf = context.user_data.get('start_num_vcf')

        renamed_files_vcf = []
        file_counter_vcf = start_num_vcf

        for file_path in uploaded_files_vcf:
            renamed_file_path = f"downloads/{new_filename_vcf}_{file_counter_vcf}.vcf"
            os.rename(file_path, renamed_file_path)
            renamed_files_vcf.append(renamed_file_path)
            file_counter_vcf += 1

        # Kirim file yang telah diganti namanya
        for renamed_file in renamed_files_vcf:
            with open(renamed_file, 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=os.path.basename(renamed_file)
                )

        # Hapus file yang telah dikirim
        for renamed_file in renamed_files_vcf:
            if os.path.exists(renamed_file):
                os.remove(renamed_file)

        await update.message.reply_text("✅ Semua file berhasil diganti namanya dan dikirim!")

        # Reset state setelah selesai
        context.user_data.clear()

    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan saat mengganti nama file: {str(e)}")
        print(f"🚨 Error: {str(e)}")

async def process_split_txt(update: Update, context: CallbackContext):
    """Memisahkan file TXT berdasarkan jumlah baris per file dan nomor urut yang diberikan."""
    try:
        uploaded_file = context.user_data.get('uploaded_file')
        if not uploaded_file:
            await update.message.reply_text("❌ Tidak ada file yang diunggah untuk diproses. Silakan unggah file terlebih dahulu.")
            return

        # Mendapatkan parameter dari user data
        split_filename = context.user_data.get('split_filename')
        start_num = context.user_data.get('start_num')
        lines_per_file = context.user_data.get('lines_per_file')

        # Membaca isi file yang diunggah
        with open(uploaded_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        print(f"DEBUG: Total lines in file: {len(lines)}")

        # Membagi file menjadi beberapa file terpisah
        split_files = []
        current_line = 0
        file_count = start_num
        while current_line < len(lines):
            split_file_name = f"{split_filename}_{file_count}.txt"
            split_file_path = f"downloads/{split_file_name}"

            # Menulis bagian file terpisah
            with open(split_file_path, 'w', encoding='utf-8') as split_file:
                split_file.writelines(lines[current_line:current_line + lines_per_file])

            split_files.append(split_file_path)
            current_line += lines_per_file
            file_count += 1

        # Mengirimkan file hasil pemisahan kembali ke pengguna
        for split_file in split_files:
            with open(split_file, 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=os.path.basename(split_file)
                )

        # Menghapus file sementara yang telah dipisah
        for split_file in split_files:
            if os.path.exists(split_file):
                os.remove(split_file)

        await update.message.reply_text(f"✅ File berhasil dipisahkan dan dikirim!")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="TEKAN START 🔄 UNTUK MEMULAI KEMBALI",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan saat memisahkan file: {str(e)}")
        print(f"🚨 Error: {str(e)}")

async def process_split_vcf(update: Update, context: CallbackContext):
    """Memisahkan file VCF berdasarkan jumlah kontak per file yang diberikan."""
    try:
        uploaded_file_vcf = context.user_data.get('uploaded_file_vcf')
        if not uploaded_file_vcf:
            await update.message.reply_text("❌ Tidak ada file yang diunggah untuk diproses. Silakan unggah file terlebih dahulu.")
            return

        # Mendapatkan parameter dari user data
        split_filename_vcf = context.user_data.get('split_filename_vcf')
        start_num_vcf = context.user_data.get('start_num_vcf')
        contacts_per_file_vcf = context.user_data.get('contacts_per_file_vcf')

        # Membaca isi file VCF yang diunggah
        with open(uploaded_file_vcf, 'r', encoding='utf-8') as file:
            vcf_data = file.read()

        contacts = vcf_data.split("END:VCARD")
        contacts = [contact.strip() + "\nEND:VCARD" for contact in contacts if contact.strip()]
        
        print(f"DEBUG: Total contacts in file: {len(contacts)}")

        # Membagi file menjadi beberapa file terpisah
        split_files = []
        current_index = 0
        file_count = start_num_vcf
        while current_index < len(contacts):
            split_file_name = f"{split_filename_vcf}_{file_count}.vcf"
            split_file_path = f"downloads/{split_file_name}"

            # Menulis bagian file terpisah
            with open(split_file_path, 'w', encoding='utf-8') as split_file:
                split_file.write("\n".join(contacts[current_index:current_index + contacts_per_file_vcf]))

            split_files.append(split_file_path)
            current_index += contacts_per_file_vcf
            file_count += 1

        # Mengirimkan file hasil pemisahan kembali ke pengguna
        for split_file in split_files:
            with open(split_file, 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=os.path.basename(split_file)
                )

        # Menghapus file sementara yang telah dipisah
        for split_file in split_files:
            if os.path.exists(split_file):
                os.remove(split_file)

        await update.message.reply_text(f"✅ File berhasil dipisahkan dan dikirim!")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="TEKAN START 🔄 UNTUK MEMULAI KEMBALI",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan saat memisahkan file: {str(e)}")
        print(f"🚨 Error: {str(e)}")


async def handle_merge_files_vcf(update: Update, context: CallbackContext):
    try:
        uploaded_files_vcf = context.user_data.get('uploaded_files_vcf', [])
        if not uploaded_files_vcf:
            await update.message.reply_text("❌ Tidak ada file untuk digabung.")
            return

        merge_filename_vcf = context.user_data.get('merge_filename_vcf')
        if not merge_filename_vcf:
            await update.message.reply_text("❌ Nama file gabungan tidak ditemukan. Silakan ulangi proses.")
            return

        output_path = f"downloads/{merge_filename_vcf}.vcf"
        os.makedirs('downloads', exist_ok=True)
        print(f"DEBUG: File gabungan akan disimpan di: {output_path}")

        with open(output_path, 'w', encoding='utf-8') as outfile:
            for file_path in uploaded_files_vcf:
                print(f"DEBUG: Menggabungkan file: {file_path}")
                with open(file_path, 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read().strip())
                    outfile.write("\n")

        with open(output_path, 'rb') as merged_file:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=merged_file,
                filename=os.path.basename(output_path)
            )
        print(f"✅ File gabungan berhasil dikirim: {output_path}")

        for temp_file in uploaded_files_vcf:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        if os.path.exists(output_path):
            os.remove(output_path)

        context.user_data.clear()
        await update.message.reply_text(f"✅ File {merge_filename_vcf}.vcf berhasil digabungkan dan dikirim!")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="TEKAN START 🔄 UNTUK MEMULAI KEMBALI",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan saat menggabungkan file: {str(e)}")
        print(f"DEBUG: Error dalam handle_merge_files_vcf: {str(e)}")

async def handle_file_vcf(update: Update, context: CallbackContext):
    """Fungsi untuk menangani file VCF yang dikirim user."""
    try:
        file = await update.message.document.get_file()
        file_name = update.message.document.file_name

        if not file_name:
            await update.message.reply_text("❌ File tidak memiliki nama. Pastikan file memiliki nama yang valid.")
            return

        if not file_name.lower().endswith('.vcf'):
            await update.message.reply_text("❌ Hanya file VCF yang dapat diterima.")
            return

        downloaded_file = f"downloads/{file_name}"
        os.makedirs('downloads', exist_ok=True)
        await file.download_to_drive(downloaded_file)
        print(f"File {file_name} berhasil diunduh ke {downloaded_file}.")
        
        if context.user_data.get('merge_mode_vcf'):
            uploaded_files_vcf = context.user_data.get('uploaded_files_vcf', [])
            uploaded_files_vcf.append(downloaded_file)
            context.user_data['uploaded_files_vcf'] = uploaded_files_vcf
            print(f"📥 DEBUG: Files uploaded so far: {uploaded_files_vcf}")

            await update.message.reply_text(f"📥 File {file_name} berhasil diunggah. Kirimkan file lainnya atau tekan 'Mulai Gabung File VCF' jika sudah selesai.")
            return
        elif context.user_data.get('waiting_for_split_vcf_file'):
            # Jika sedang dalam mode pemisahan file VCF
            context.user_data['uploaded_file_vcf'] = downloaded_file  # Simpan file yang diupload untuk diproses lebih lanjut
            await update.message.reply_text(f"📥 File {file_name} berhasil diunggah untuk dipisah. Sekarang memulai pemisahan file.")
            await process_split_vcf(update, context)  # Panggil fungsi untuk memisahkan file
            return
        

        elif context.user_data.get('waiting_for_vcf_files'):
            # Menangani file yang diunggah oleh pengguna
            await handle_uploaded_vcf_files(update, context)
            return

    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)}")
        print(f"🚨 Error: {str(e)}")
async def handle_merge_files_txt(update: Update, context: CallbackContext):
    try:
        uploaded_files = context.user_data.get('uploaded_files', [])
        if not uploaded_files:
            await update.message.reply_text("❌ Tidak ada file untuk digabung.")
            return

        if not all(f.endswith('.txt') for f in uploaded_files):
            await update.message.reply_text("❌ Hanya file TXT yang dapat digabung.")
            return

        merge_filename = context.user_data.get('merge_filename')
        if not merge_filename:
            await update.message.reply_text("❌ Nama file gabungan tidak ditemukan. Silakan ulangi proses.")
            return

        output_path = f"downloads/{merge_filename}.txt"
        print(f"DEBUG: File gabungan akan disimpan di: {output_path}")

        with open(output_path, 'w', encoding='utf-8') as outfile:
            for file_path in uploaded_files:
                print(f"DEBUG: Menggabungkan file: {file_path}")
                with open(file_path, 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read().strip())
                    outfile.write("\n")

        with open(output_path, 'rb') as merged_file:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=merged_file,
                filename=os.path.basename(output_path)
            )
        print(f"✅ File gabungan berhasil dikirim: {output_path}")

        for temp_file in uploaded_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        if os.path.exists(output_path):
            os.remove(output_path)

        context.user_data.clear()
        await update.message.reply_text(f"✅ File {merge_filename}.txt berhasil digabungkan dan dikirim!")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="TEKAN START 🔄 UNTUK MEMULAI KEMBALI",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan saat menggabungkan file: {str(e)}")
        print(f"DEBUG: Error dalam handle_merge_files_txt: {str(e)}")


# Timer untuk deteksi pengunggahan selesai
async def start_conversion_timer(context, delay=5):
    """Menunggu beberapa detik sebelum memulai konversi, memastikan semua file telah diunggah."""
    await asyncio.sleep(delay)

    if context.user_data.get('processing', False):
        return  # Jika sudah diproses sebelumnya, abaikan

    context.user_data['processing'] = True  # Set flag bahwa proses sedang berjalan

    uploaded_files = context.user_data.get("uploaded_files", [])
    if not uploaded_files:
        print("⛔ Tidak ada file yang diunggah, membatalkan proses konversi.")
        context.user_data['processing'] = False
        return

    await context.bot.send_message(
        chat_id=context.user_data['chat_id'],
        text="📂 Sedang memproses file... Harap tunggu."
    )

    contact_name_pattern = context.user_data.get("contact_name_pattern", "Contact")
    vcf_filename_pattern = context.user_data.get("vcf_filename_pattern", "FileVCF")
    starting_number = context.user_data.get("starting_numbers", 1)

    vcf_files = convert_multiple_txt_to_vcf(
        uploaded_files,
        contact_name_pattern,
        vcf_filename_pattern,
        starting_number
    )

    if vcf_files:
        for vcf_file in vcf_files:
            with open(vcf_file, 'rb') as doc:
                await context.bot.send_document(
                    chat_id=context.user_data['chat_id'],
                    document=doc,
                    filename=os.path.basename(vcf_file)
                )
                print(f"✅ File {vcf_file} berhasil dikirim ke user.")

            if os.path.exists(vcf_file):
                os.remove(vcf_file)
                print(f"🗑️ File {vcf_file} telah dihapus.")

    for txt_file in uploaded_files:
        if os.path.exists(txt_file):
            os.remove(txt_file)
            print(f"🗑️ File sementara {txt_file} telah dihapus.")

    context.user_data.clear()
    await context.bot.send_message(
        chat_id=context.user_data['chat_id'],
        text="✅ Semua file VCF telah dikonversi dan dikirim!"
    )
    await context.bot.send_message(
        chat_id=context.user_data['chat_id'],
        text="TEKAN START 🔄 UNTUK MEMULAI KEMBALI",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Start 🔄")]], resize_keyboard=True)
    )


def restricted_handler(handler_func):
    async def wrapper(update: Update, context: CallbackContext):
        if update.effective_chat.id in ALLOWED_CHAT_ID:
            await handler_func(update, context)
        else:
            await update.message.reply_text(
                "Anda tidak memiliki akses, silahkan hubungi @matttt36 untuk membeli akses."
            )
    return wrapper


async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != 1188243355:
        await update.message.reply_text("\u274C Anda tidak memiliki izin untuk menggunakan perintah ini.")
        return

    await update.message.reply_text(
        "Masukkan ID pengguna baru yang ingin ditambahkan:\n\nTekan 'Start \ud83d\udd04' untuk membatalkan.",
        reply_markup=ReplyKeyboardMarkup([["Start \ud83d\udd04"]], resize_keyboard=True)
    )
    context.user_data['waiting_for_user_id'] = True

def ensure_users_file():
    """Ensure the allowed_users.json file exists."""
    if not os.path.exists('allowed_users.json'):
        with open('allowed_users.json', 'w') as f:
            json.dump({"users": []}, f, indent=4)

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != 1188243355:
        await update.message.reply_text("\u274C Anda tidak memiliki izin untuk menggunakan perintah ini.")
        return
    try:
        with open('allowed_users.json', 'r') as f:
            data = json.load(f)
        if not data['users']:
            await update.message.reply_text("\u2139\ufe0f Tidak ada pengguna terdaftar.")
            return

        # Prepare the user list with ID, username, and duration
        user_list = "\ud83d\udccb Daftar Pengguna:\n\n"
        current_date = datetime.now()
        for user in data['users']:
            role = user.get('role', 'Tidak diketahui')
            if "temporary" in role:
                duration_days = int(role.split('_')[1])
                added_date = datetime.strptime(user['added_date'], "%Y-%m-%d")
                expiry_date = added_date + timedelta(days=duration_days)
                remaining_days = (expiry_date - current_date).days
                duration = f"{remaining_days} hari" if remaining_days > 0 else "Kedaluwarsa"
            else:
                duration = "Permanen"

            user_list += f"ID: {user['id']}\nUsername: {user['username']}\nSisa Durasi: {duration}\n-------------------\n"

        await update.message.reply_text(
            f"{user_list}\nSilakan masukkan ID pengguna yang ingin dihapus:\n\nTekan 'Start 🔄' untuk membatalkan.",
            reply_markup=ReplyKeyboardMarkup([["Start 🔄"]], resize_keyboard=True)
        )
        context.user_data['waiting_for_user_id_to_remove'] = True
    except Exception as e:
        await update.message.reply_text(f"\u274C Terjadi kesalahan: {str(e)}")

async def confirm_user_removal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('confirm_removal'):
        if update.message.text == "Konfirmasi":
            user_to_remove = context.user_data.get('user_to_remove')
            try:
                with open('allowed_users.json', 'r') as f:
                    data = json.load(f)

                # Remove the user from the list
                data['users'] = [user for user in data['users'] if user['id'] != user_to_remove['id']]

                with open('allowed_users.json', 'w') as f:
                    json.dump(data, f, indent=4)

                await update.message.reply_text(
                    f"\u2705 Pengguna dengan ID {user_to_remove['id']} dan username {user_to_remove['username']} telah dihapus."
                )
                context.user_data.clear()
            except Exception as e:
                await update.message.reply_text(f"\u274C Terjadi kesalahan: {str(e)}")
        elif update.message.text == "Start 🔄":
            context.user_data.clear()
            await update.message.reply_text(
                "\u274C Proses penghapusan dibatalkan.",
                reply_markup=ReplyKeyboardMarkup([["Start 🔄"]], resize_keyboard=True)
            )

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Periksa apakah pengguna memiliki izin (hanya admin dengan ID tertentu)
    if update.effective_user.id != 1188243355:  # Ganti ID admin sesuai kebutuhan
        await update.message.reply_text("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")
        return
    try:
        ensure_users_file()  # Pastikan file allowed_users.json ada

        with open('allowed_users.json', 'r') as f:
            data = json.load(f)

        if not data['users']:
            await update.message.reply_text("ℹ️ Tidak ada pengguna terdaftar.")
            return

        user_list = "📋 *Daftar Pengguna Terdaftar:*\n\n"
        current_date = datetime.now()

        for user in data['users']:
            # Ambil informasi pengguna
            user_id = user.get('id', 'Tidak diketahui')
            username = user.get('username', '(Tidak ada username)')
            role = user.get('role', 'Tidak diketahui')
            added_date = user.get('added_date', 'Tidak diketahui')

            # Interpretasi durasi
            if role.startswith("temporary_"):
                try:
                    duration_days = int(role.split("_")[1])
                    added_datetime = datetime.strptime(added_date, "%Y-%m-%d")
                    expiry_date = added_datetime + timedelta(days=duration_days)
                    remaining_days = (expiry_date - current_date).days

                    if remaining_days > 0:
                        role_desc = f"{remaining_days} hari tersisa"
                    else:
                        role_desc = "Kedaluwarsa"
                except Exception:
                    role_desc = "Durasi tidak valid"
            elif role == "permanent":
                role_desc = "Permanen"
            else:
                role_desc = "Tidak diketahui"

            # Tambahkan ke daftar
            user_list += (
                f"🆔 *ID*: `{user_id}`\n"
                f"👤 *Username*: @{username}\n"
                f"📅 *Tanggal Ditambahkan*: {added_date}\n"
                f"⏳ *Durasi*: {role_desc}\n"
                "---------------------------------------------------\n"
            )

        await update.message.reply_text(
            user_list,
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)}")
async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan detail ID, username, dan sisa durasi akses pengguna."""
    user_id = update.effective_user.id
    ensure_users_file()  # Pastikan file allowed_users.json ada

    try:
        with open('allowed_users.json', 'r') as f:
            data = json.load(f)

        # Cari data pengguna berdasarkan ID
        user_data = next((user for user in data['users'] if user['id'] == user_id), None)

        if not user_data:
            await update.message.reply_text(
                "❌ Anda tidak terdaftar sebagai pengguna yang memiliki akses ke bot ini."
            )
            return

        # Ambil detail pengguna
        username = user_data.get('username', '(Tidak ada username)')
        role = user_data.get('role', 'Tidak diketahui')
        added_date = user_data.get('added_date', 'Tidak diketahui')

        # Interpretasi durasi akses
        if "temporary" in role:
            try:
                duration_days = int(role.split('_')[1])
                added_datetime = datetime.strptime(added_date, "%Y-%m-%d")
                expiry_date = added_datetime + timedelta(days=duration_days)
                remaining_days = (expiry_date - datetime.now()).days
                if remaining_days > 0:
                    role_desc = f"{remaining_days} hari tersisa"
                else:
                    role_desc = "Kedaluwarsa"
            except Exception:
                role_desc = "Durasi tidak valid"
        elif role == "permanent":
            role_desc = "Permanen"
        else:
            role_desc = "Tidak diketahui"

        # Tampilkan status pengguna
        await update.message.reply_text(
            f"📋 *Status Anda:*\n\n"
            f"🆔 *ID*: `{user_id}`\n"
            f"👤 *Username*: @{username}\n"
            f"📅 *Tanggal Ditambahkan*: {added_date}\n"
            f"⏳ *Durasi*: {role_desc}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan saat memeriksa status: {str(e)}")


async def add_user_with_duration(update: Update, context: ContextTypes.DEFAULT_TYPE, duration: str):
    ensure_users_file()

    new_user_id = context.user_data.get('new_user_id')
    username = context.user_data.get('new_username')
    role = "permanent" if duration == "Permanen" else f"temporary_{duration.split(' ')[0]}"

    try:
        with open('allowed_users.json', 'r') as f:
            data = json.load(f)

        if not any(user['id'] == new_user_id for user in data['users']):
            new_user = {
                "id": new_user_id,
                "username": username,
                "role": role,
                "added_date": datetime.now().strftime("%Y-%m-%d")
            }
            data['users'].append(new_user)

            with open('allowed_users.json', 'w') as f:
                json.dump(data, f, indent=4)

            await update.message.reply_text(
                f"\u2705 Pengguna dengan ID {new_user_id} dan username {username} telah ditambahkan dengan durasi {duration}."
            )
        else:
            await update.message.reply_text(f"\u274C Pengguna dengan ID {new_user_id} sudah ada dalam daftar.")
    except Exception as e:
        await update.message.reply_text(f"\u274C Terjadi kesalahan: {str(e)}")

    context.user_data.clear()

async def cleanup_expired_users(context: ContextTypes.DEFAULT_TYPE):
    ensure_users_file()

    with open('allowed_users.json', 'r') as f:
        data = json.load(f)

    if not data['users']:
        return

    current_date = datetime.now()
    updated_users = []
    expired_users = []

    for user in data['users']:
        if "temporary" in user['role']:
            duration_days = int(user['role'].split('_')[1])
            added_date = datetime.strptime(user['added_date'], "%Y-%m-%d")
            expiry_date = added_date + timedelta(days=duration_days)

            if current_date >= expiry_date:
                expired_users.append(user)
            else:
                updated_users.append(user)
        else:
            updated_users.append(user)

    with open('allowed_users.json', 'w') as f:
        json.dump({"users": updated_users}, f, indent=4)

    if expired_users:
        admin_id = 1188243355
        message = "\u26a0\ufe0f Pengguna berikut telah kedaluwarsa dan dihapus:\n\n"
        for user in expired_users:
            message += f"ID: {user['id']}, Username: {user['username']}, Role: {user['role']}\n"
        await context.bot.send_message(chat_id=admin_id, text=message)

    print("\u2705 Cleanup selesai. Pengguna yang kedaluwarsa telah dihapus.")

async def ping(context: ContextTypes.DEFAULT_TYPE):
    logging.info("Ping berhasil dikirim.")
async def send_broadcast(application, message):
    """Mengirim pesan broadcast ke semua pengguna yang terdaftar."""
    ensure_users_file()
    with open(ALLOWED_USERS_FILE, 'r') as f:
        data = json.load(f)
    
    for user in data['users']:
        chat_id = user['id']
        try:
            await application.bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            print(f"Error mengirim pesan ke {chat_id}: {e}")
async def update_usernames():
    """Memeriksa dan memperbarui username, first name, dan last name pengguna jika berubah."""
    if not os.path.exists(ALLOWED_USERS_FILE):
        return

    with open(ALLOWED_USERS_FILE, "r") as f:
        data = json.load(f)

    BOT_TOKEN = "7328544720:AAHZsyEU2c9u0c5kom4XmDKhcawidFnoUI0"
    bot = Bot(token=BOT_TOKEN)
    admin_chat_id = 1188243355  # ID admin yang menerima notifikasi perubahan
    updated = False
    change_messages = []

    for user in data["users"]:
        user_id = user["id"]

        try:
            chat = await bot.get_chat(user_id)
            new_username = chat.username if chat.username else "(Tidak ada username)"
            new_first_name = chat.first_name if chat.first_name else "(Tidak ada first name)"
            new_last_name = chat.last_name if chat.last_name else "(Tidak ada last name)"

            changes = []

            if user.get("username") != new_username:
                user["username"] = new_username
                changes.append(f"🔄 Username: @{new_username}")

            if user.get("first_name") != new_first_name:
                user["first_name"] = new_first_name
                changes.append(f"📝 First Name: {new_first_name}")

            if user.get("last_name") != new_last_name:
                user["last_name"] = new_last_name
                changes.append(f"📝 Last Name: {new_last_name}")

            if changes:
                updated = True
                change_messages.append(f"🆔 ID: `{user_id}`\n" + "\n".join(changes))

        except Exception as e:
            print(f"⚠️ Gagal mendapatkan data untuk ID {user_id}: {e}")

    if updated:
        with open(ALLOWED_USERS_FILE, "w") as f:
            json.dump(data, f, indent=4)

        # Gabungkan semua perubahan dalam satu pesan
        final_message = "🔔 *Perubahan Data Pengguna:*\n\n" + "\n\n".join(change_messages)

        await bot.send_message(
            chat_id=admin_chat_id,
            text=final_message,
            parse_mode="Markdown"
        )

        print("✅ allowed_users.json telah diperbarui!")

async def start_scheduler(application):
    """Menjadwalkan pembaruan username, first name, dan last name setiap 1 menit."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(update_usernames, "interval", minutes=1)
    scheduler.start()
    print("🕒 Scheduler untuk update username aktif setiap 10 menit.")

async def main():
    application = ApplicationBuilder().token("7847631843:AAFg_NVFieDW4im3_Qq_xOCo1PFaddey704").build()

    # Kirim broadcast saat bot aktif
    broadcast_message = (
        "️🔔 Bot baru saja di update dan sudah Aktif.🔔 \n"
        "\n"
        "⚠️ Silahkan tekan /start untuk memulai kembali. ⚠️"
    )
    await send_broadcast(application, broadcast_message)
    await start_scheduler(application)

    # Scheduler setup
    scheduler = AsyncIOScheduler()
    scheduler.add_job(cleanup_expired_users, IntervalTrigger(hours=24), args=[application.job_queue])
    scheduler.start()
    # Conversation handler setup
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text),
            MessageHandler(filters.Document.FileExtension("txt"), handle_file_txt),
            MessageHandler(filters.Document.FileExtension("vcf"), handle_file_vcf),
        ]

        },
        fallbacks=[CommandHandler('start', start)],
    )
    # Adding handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('adduser', restricted_handler(add_user)))
    application.add_handler(CommandHandler('removeuser', restricted_handler(remove_user)))
    application.add_handler(CommandHandler('listusers', restricted_handler(list_users)))
    
    # Run polling
    await application.run_polling()
if __name__ == '__main__':
    import asyncio
    asyncio.run(main())  # Correct way to run the main async function

