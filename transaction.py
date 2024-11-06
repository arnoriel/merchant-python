# transaction.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
import json
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
logging.basicConfig(level=logging.DEBUG)

transaction_bp = Blueprint('transaction', __name__)

# Load data dari data.json
def load_data():
    with open("data.json") as f:
        return json.load(f)

# Simpan data ke data.json
def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

# Route untuk mencari pelanggan berdasarkan NIK
@transaction_bp.route('/transaction/search', methods=['GET', 'POST'])
@jwt_required()
def search_nik():
    if request.method == 'POST':
        nik = request.form.get('nik')
        data = load_data()
        
        # Mencari customer berdasarkan NIK
        customer = next((c for c in data["customers"] if c["nik"] == nik), None)
        if customer:
            return redirect(url_for('transaction.transaction_page', customer_id=customer["id"]))
        else:
            flash("NIK tidak ditemukan", "error")
            return render_template('search_nik.html')  # Tetap di halaman pencarian jika NIK tidak ditemukan
    
    return render_template('search_nik.html')  # Mengganti template dari superadmin ke search_nik.html

# Halaman transaksi setelah NIK ditemukan
@transaction_bp.route('/transaction/<customer_id>', methods=['GET', 'POST'])
@jwt_required()
def transaction_page(customer_id):
    data = load_data()
    current_user_id = get_jwt_identity()
    
    # Ambil data user dan customer
    user = next((u for u in data["users"] if u["id"] == current_user_id), None)
    customer = next((c for c in data["customers"] if c["id"] == customer_id), None)
    
    if not user or not customer:
        flash("User atau Customer tidak ditemukan", "error")
        return redirect(url_for('transaction.search_nik'))
    
    # Tambahkan pengecekan apakah tabung customer sudah mencapai batas
    if customer["tabung"] >= customer["max_tabung"]:
        return render_template('transaction.html', user=user, customer=customer, 
                               error_message="Tidak bisa melakukan proses transaksi lagi, sudah mencapai batas kewajaran pembelian tabung")

    if request.method == 'POST':
        # Mendapatkan jumlah tabung yang akan dipindahkan
        jumlah_tabung = int(request.form.get('jumlah_tabung'))
        
        # Validasi jumlah tabung
        if jumlah_tabung <= user["tabung"] and (customer["tabung"] + jumlah_tabung) <= customer["max_tabung"]:
            return render_template('confirmation.html', user=user, customer=customer, jumlah_tabung=jumlah_tabung)
        else:
            flash("Jumlah tabung tidak valid", "error")
    
    return render_template('transaction.html', user=user, customer=customer)

# Halaman konfirmasi transaksi
@transaction_bp.route('/transaction/confirm', methods=['POST'])
@jwt_required()
def confirm_transaction():
    data = load_data()
    current_user_id = get_jwt_identity()
    
    # Mendapatkan data yang diperlukan dari form
    customer_id = request.form.get('customer_id')
    jumlah_tabung = int(request.form.get('jumlah_tabung'))
    
    # Ambil user dan customer dari data
    user = next((u for u in data["users"] if u["id"] == current_user_id), None)
    customer = next((c for c in data["customers"] if c["id"] == customer_id), None)
    
    if user and customer:
        # Proses transaksi
        user["tabung"] -= jumlah_tabung
        customer["tabung"] += jumlah_tabung
        save_data(data)
        
        # Kirim user dan customer ke template struct.html
        return render_template('struct.html', user=user, customer=customer, jumlah_tabung=jumlah_tabung)
    
    flash("Terjadi kesalahan saat melakukan transaksi", "error")
    return redirect(url_for('transaction.transaction_page', customer_id=customer_id))
