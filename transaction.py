# transaction.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import json
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import uuid
from datetime import datetime
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

# Endpoint untuk pencarian pelanggan berdasarkan NIK
@transaction_bp.route('/transaction/search', methods=['GET', 'POST'])
def search_nik():
    if request.method == 'POST':
        nik = request.form.get('nik')
        data = load_data()

        # Mencari customer berdasarkan NIK
        customer = next((c for c in data["customers"] if c["nik"] == nik), None)
        if customer:
            return redirect(url_for('transaction.transaction_page', customer_id=customer["id"]))
        
        # Jika NIK tidak ditemukan, tampilkan pesan flash
        flash("NIK tidak ditemukan", "error")
        
        # Cek user_role dari session dan render template yang sesuai tanpa redirect
        user_role = session.get('user_role')
        if user_role == "superadmin":
            return render_template('userpages/superadmin.html')
        elif user_role == "admin":
            return render_template('userpages/admin.html')
        elif user_role == "cashier":
            return render_template('userpages/cashier.html')
        
        # Jika tidak ada user role, langsung kembalikan ke halaman dashboard default (misalnya ke 'admin')
        flash("Role tidak ditemukan. Mengarah ke halaman admin.", "warning")
        return render_template('userpages/admin.html')

    # Jika request method GET, langsung arahkan ke halaman sesuai peran
    user_role = session.get('user_role')
    if user_role == "superadmin":
        return render_template('userpages/superadmin.html')
    elif user_role == "admin":
        return render_template('userpages/admin.html')
    elif user_role == "cashier":
        return render_template('userpages/cashier.html')

    # Jika tidak ada user role, langsung kembalikan ke halaman dashboard default
    flash("Role tidak ditemukan. Mengarah ke halaman admin.", "warning")
    return render_template('userpages/admin.html')

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
        return render_template('transactions/transaction.html', user=user, customer=customer, 
                               error_message="Tidak bisa melakukan proses transaksi lagi, sudah mencapai batas kewajaran pembelian tabung")

    if request.method == 'POST':
        # Mendapatkan jumlah tabung yang akan dipindahkan
        jumlah_tabung = int(request.form.get('jumlah_tabung'))
        
        # Validasi jumlah tabung
        if jumlah_tabung <= user["tabung"] and (customer["tabung"] + jumlah_tabung) <= customer["max_tabung"]:
            return render_template('transactions/confirmation.html', user=user, customer=customer, jumlah_tabung=jumlah_tabung)
        else:
            flash("Jumlah tabung tidak valid", "error")
    
    return render_template('transactions/transaction.html', user=user, customer=customer)

# Halaman konfirmasi transaksi
@transaction_bp.route('/transaction/confirm', methods=['POST'])
@jwt_required()
def confirm_transaction():
    data = load_data()
    current_user_id = get_jwt_identity()
    
    customer_id = request.form.get('customer_id')
    jumlah_tabung = int(request.form.get('jumlah_tabung'))
    
    user = next((u for u in data["users"] if u["id"] == current_user_id), None)
    customer = next((c for c in data["customers"] if c["id"] == customer_id), None)
    
    if user and customer:
        user["tabung"] -= jumlah_tabung
        customer["tabung"] += jumlah_tabung

        # Record the transaction in history with a unique ID
        transaction_record = {
            "id": str(uuid.uuid4()),  # Generate a unique ID for each transaction
            "customer_name": customer["name"],
            "customer_nik": customer["nik"],
            "jumlah_tabung": jumlah_tabung,
            "username_responsible": user["username"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        data["history"].append(transaction_record)
        save_data(data)

        return render_template('transactions/struct.html', user=user, customer=customer, jumlah_tabung=jumlah_tabung)

    flash("Error processing transaction", "error")
    return redirect(url_for('transaction.transaction_page', customer_id=customer_id))


@transaction_bp.route('/transaction/history')
@jwt_required()
def transaction_history():
    data = load_data()
    current_user_id = get_jwt_identity()
    
    # Retrieve the current user
    user = next((u for u in data["users"] if u["id"] == current_user_id), None)
    
    if not user:
        flash("User not found", "error")
        return redirect(url_for('transaction.search_nik'))
    
    # Filter the transaction history for the current user
    user_history = [record for record in data["history"] if record["username_responsible"] == user["username"]]
    
    return render_template('transactions/history.html', history=user_history, user=user)


@transaction_bp.route('/transaction/history/<string:transaction_id>')
@jwt_required()
def transaction_detail(transaction_id):
    data = load_data()
    
    # Find the specific transaction record by its unique ID
    record = next((record for record in data["history"] if record["id"] == transaction_id), None)
    
    if record:
        return render_template('transactions/transaction_detail.html', record=record)
    else:
        flash("Transaction record not found", "error")
        return redirect(url_for('transaction.transaction_history'))

@transaction_bp.route('/transaction/cancel/<string:transaction_id>', methods=['POST'])
@jwt_required()
def cancel_transaction(transaction_id):
    data = load_data()
    current_user_id = get_jwt_identity()

    user = next((u for u in data["users"] if u["id"] == current_user_id), None)
    record = next((r for r in data["history"] if r["id"] == transaction_id), None)

    if not record:
        flash("Transaksi tidak ditemukan", "error")
        return redirect(url_for('transaction.transaction_history'))

    reasons = request.form.get('reasons')  # Mendapatkan alasan dari user
    
    # Cari user dan customer berdasarkan transaksi
    user = next((u for u in data["users"] if u["username"] == record["username_responsible"]), None)
    customer = next((c for c in data["customers"] if c["nik"] == record["customer_nik"]), None)

    if user and customer:
        jumlah_tabung = record["jumlah_tabung"]

        # Pulihkan jumlah tabung
        user["tabung"] += jumlah_tabung
        customer["tabung"] -= jumlah_tabung

        # Tambahkan record ke tabel cancel
        cancel_record = {
            "id": str(uuid.uuid4()),
            "original_transaction_id": transaction_id,
            "customer_name": record["customer_name"],
            "customer_nik": record["customer_nik"],
            "jumlah_tabung": jumlah_tabung,
            "username_responsible": user["username"],
            "cancel_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reasons": reasons
        }
        data["cancel"].append(cancel_record)

        # Hapus transaksi dari history
        data["history"] = [r for r in data["history"] if r["id"] != transaction_id]

        # Simpan perubahan
        save_data(data)

        flash("Transaksi berhasil dibatalkan dan tabung telah dipulihkan", "success")
    else:
        flash("User atau Customer tidak ditemukan untuk pembatalan transaksi", "error")

    return redirect(url_for('transaction.transaction_history'))

@transaction_bp.route('/transaction/cancel/history')
@jwt_required()
def cancel_history():
    data = load_data()
    current_user_id = get_jwt_identity()

    # Ambil user yang sedang login
    user = next((u for u in data["users"] if u["id"] == current_user_id), None)

    if not user:
        flash("User tidak ditemukan", "error")
        return redirect(url_for('transaction.transaction_history'))

    # Ambil semua riwayat pembatalan tanpa filter pengguna
    all_cancel_history = data["cancel"]

    return render_template('transactions/cancel.html', cancel_history=all_cancel_history, user=user)

@transaction_bp.route('/transaction/cancel/history/<string:cancel_id>')
@jwt_required()
def cancel_detail(cancel_id):
    data = load_data()

    # Cari record pembatalan berdasarkan ID
    cancel_record = next((record for record in data["cancel"] if record["id"] == cancel_id), None)

    if cancel_record:
        return render_template('transactions/cancel_detail.html', record=cancel_record)
    else:
        flash("Record pembatalan tidak ditemukan", "error")
        return redirect(url_for('transaction.cancel_history'))

