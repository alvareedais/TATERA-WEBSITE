import os
import re
import cv2
import numpy as np
import easyocr
from flask import Flask, request, jsonify, render_template
import base64

app = Flask(__name__, template_folder='.', static_folder='.')

# Inisialisasi EasyOCR Reader sekali saja saat server berjalan agar cepat
print("Sedang memuat model EasyOCR (English & Indonesian)...")
reader = easyocr.Reader(['en', 'id'], gpu=False)
print("Model EasyOCR siap digunakan!")

@app.route('/')
def index():
    # Mengarah langsung ke file scan-nota.html Anda
    return render_template('scan-nota.html')

@app.route('/proses-ocr', methods=['POST'])
def proses_ocr():
    try:
        data = request.json
        if not data or 'image' not in data:
            return jsonify({'status': 'error', 'message': 'Data gambar tidak ditemukan'}), 400

        # 1. DECODE IMAGE DARI BASE64 KAMERA WEB
        data_gambar = data['image'].split(',')[1]
        img_bytes = base64.b64decode(data_gambar)
        nparr = np.frombuffer(img_bytes, np.uint8)
        citra_asli = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if citra_asli is None:
            return jsonify({'status': 'error', 'message': 'Gagal membaca format citra'}), 400

        # =========================================================================
        # PENGOLAHAN CITRA & LOGIKA OCR KELOMPOK ANDA
        # =========================================================================
        citra_gray = cv2.cvtColor(citra_asli, cv2.COLOR_BGR2GRAY)
        lebar_target = 1000
        skala = lebar_target / citra_gray.shape[1]
        tinggi_target = int(citra_gray.shape[0] * skala)
        citra_bersih = cv2.resize(citra_gray, (lebar_target, tinggi_target), interpolation=cv2.INTER_AREA)

        # Proses OCR menggunakan model EasyOCR
        hasil_raw = reader.readtext(citra_bersih, detail=1, paragraph=False, adjust_contrast=True)
        hasil_raw.sort(key=lambda x: (x[0][0][1] + x[0][2][1]) / 2)

        baris_teks = []
        baris_sekarang = []
        y_sebelumnya = None
        toleransi_y = 15 

        for bbox, teks, prob in hasil_raw:
            y_tengah = (bbox[0][1] + bbox[2][1]) / 2
            x_tengah = (bbox[0][0] + bbox[1][0]) / 2

            if y_sebelumnya is None:
                baris_sekarang.append((x_tengah, teks))
                y_sebelumnya = y_tengah
            elif abs(y_tengah - y_sebelumnya) < toleransi_y:
                baris_sekarang.append((x_tengah, teks))
            else:
                baris_sekarang.sort(key=lambda x: x[0])
                baris_teks.append(" ".join([t[1] for t in baris_sekarang]))
                baris_sekarang = [(x_tengah, teks)]
                y_sebelumnya = y_tengah

        if baris_sekarang:
            baris_sekarang.sort(key=lambda x: x[0])
            baris_teks.append(" ".join([t[1] for t in baris_sekarang]))

        # AUTOMATIC PARSING
        DATABASE_NAMA_TOKO = 'Tidak Terdeteksi'
        DATABASE_TANGGAL   = 'Tidak Terdeteksi'
        DATABASE_TOTAL     = 'Tidak Terdeteksi'
        DAFTAR_BARANG      = []

        bulan_list = ['jan', 'feb', 'mar', 'apr', 'mei', 'may', 'jun', 'jul', 'agu', 'aug', 'sep', 'okt', 'oct', 'nov', 'des', 'dec']

        for baris in baris_teks[:5]:
            baris_lower = baris.lower()
            if any(kwd in baris_lower for kwd in ['cv', 'ud', 'pt', 'toko', 'budi', 'jaya', 'maju', 'bersama', 'meidina']):
                toko_nama = re.split(r'tanggal', baris, flags=re.IGNORECASE)[0]
                DATABASE_NAMA_TOKO = re.sub(r'[^\w\s\.\-]', '', toko_nama).strip()
                break

        for baris in baris_teks:
            baris_clean = baris.strip()
            kata_kata = baris_clean.split()
            kata_fixed = []
            for k in kata_kata:
                if 'rp' in k.lower() or any(c.isdigit() for c in k):
                    k_num = k.replace('O', '0').replace('o', '0').replace('l', '1').replace('I', '1')
                    kata_fixed.append(k_num)
                else:
                    kata_fixed.append(k)
            baris_clean = " ".join(kata_fixed)
            baris_lower = baris_clean.lower()

            match_tgl = re.search(r'\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}', baris_clean)
            if match_tgl:
                DATABASE_TANGGAL = match_tgl.group()
            elif any(bln in baris_lower for bln in bulan_list) and any(c.isdigit() for c in baris_clean) and DATABASE_TANGGAL == 'Tidak Terdeteksi':
                DATABASE_TANGGAL = baris_clean

            if any(kwd in baris_lower for kwd in ['jumlah', 'total', 'sisa', 'kembali', 'tunai', 'perhatian', 'bayar']):
                angka_total = re.findall(r'\d{1,3}(?:[\.\,]\d{3})+', baris_clean)
                if angka_total:
                    DATABASE_TOTAL = f"Rp {int(re.sub(r'[\.\,]', '', angka_total[-1])):,}".replace(",", ".")
                continue

            harga_matches = re.findall(r'\d{1,3}(?:[\.\,]\d{3})+', baris_clean)
            if harga_matches:
                harga_ints = [int(re.sub(r'[\.\,]', '', h)) for h in harga_matches]
                subtotal = harga_ints[-1]
                harga_satuan = harga_ints[-2] if len(harga_ints) >= 2 else subtotal

                teks_sisa = baris_clean
                for hm in harga_matches:
                    teks_sisa = teks_sisa.replace(hm, '', 1)

                qty_match = re.search(r'\b(\d{1,3})\b', teks_sisa)
                qty = int(qty_match.group(1)) if qty_match else 1

                nama_barang = teks_sisa
                if qty_match:
                    nama_barang = nama_barang.replace(qty_match.group(1), '', 1)
                nama_barang = re.sub(r'[^\w\s\-\/]', '', nama_barang).strip()
                nama_barang = re.sub(r'\b(dus|sachet|kg|pcs)\b', '', nama_barang, flags=re.IGNORECASE).strip()

                if len(nama_barang) > 2 and not any(kwd in nama_barang.lower() for kwd in ['harga', 'jumlah', 'nama barang', 'banyaknya']):
                    DAFTAR_BARANG.append({
                        'nama': nama_barang,
                        'qty': qty,
                        'harga_satuan': f"Rp {harga_satuan:,}".replace(",", "."),
                        'subtotal': f"Rp {subtotal:,}".replace(",", ".")
                    })

        # Kembalikan hasil olahan citra dalam format objek JSON ke Antarmuka Web
        return jsonify({
            'status': 'success',
            'toko': DATABASE_NAMA_TOKO,
            'tanggal': DATABASE_TANGGAL,
            'total': DATABASE_TOTAL,
            'barang': DAFTAR_BARANG
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)