from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
import logging

# ========== Logging ==========
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ========== Flask App ==========
app = Flask(__name__)
app.secret_key = '09871234'  # production me env var use karein

# ========== Database ==========
def get_db():
    try:
        conn_str = (
            "Driver={ODBC Driver 18 for SQL Server};"
            "Server=DESKTOP-NALQG66;"
            "Database=diseasedetectiondb;"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
        return pyodbc.connect(conn_str)
    except pyodbc.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise


# ========== Routes ==========
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = None
        cursor = None
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            email = request.form.get('email', '').strip()
            name = request.form.get('name', '').strip()
            age = request.form.get('age', '').strip()
            gender = request.form.get('gender', '').strip()
            height = request.form.get('height', '').strip()
            weight = request.form.get('weight', '').strip()
            blood_type = request.form.get('blood_type', '').strip()  # IMPORTANT

            # Required fields
            if not all([username, password, email, name, age, gender, blood_type]):
                flash('Please fill all required fields (including Blood Type).', 'error')
                return render_template('register.html')

            # Validate ranges/types
            try:
                age_i = int(age)
            except ValueError:
                flash('Age must be a number.', 'error')
                return render_template('register.html')

            try:
                height_f = float(height) if height else None
                weight_f = float(weight) if weight else None
            except ValueError:
                flash('Height/Weight must be numeric.', 'error')
                return render_template('register.html')

            # Optional: enforce valid blood types to match DB CHECK constraint
            valid_bloods = {'A+','A-','B+','B-','O+','O-','AB+','AB-'}
            if blood_type not in valid_bloods:
                flash('Invalid blood type selected.', 'error')
                return render_template('register.html')

            hashed_password = generate_password_hash(password)

            conn = get_db()
            cursor = conn.cursor()

            # Dup checks
            cursor.execute("SELECT 1 FROM Users WHERE username = ?", (username,))
            if cursor.fetchone():
                flash('Username already exists!', 'error')
                return render_template('register.html')

            cursor.execute("SELECT 1 FROM Users WHERE email = ?", (email,))
            if cursor.fetchone():
                flash('Email already registered!', 'error')
                return render_template('register.html')

            # Insert user
            cursor.execute("""
                INSERT INTO Users (username, password, email)
                OUTPUT INSERTED.user_id
                VALUES (?, ?, ?)
            """, (username, hashed_password, email))
            user_id = int(cursor.fetchone()[0])

            # Insert patient (7 columns)
            cursor.execute("""
                INSERT INTO Patients (user_id, name, age, gender, height, weight, blood_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, name, age_i, gender, height_f, weight_f, blood_type))

            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            if conn:
                conn.rollback()
            logger.exception("Registration error")
            flash(f"Registration failed: {e}", 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = None
        cursor = None
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT U.user_id, U.password, P.patient_id 
                FROM Users U
                JOIN Patients P ON U.user_id = P.user_id 
                WHERE U.username = ?
            """, (username,))

            user = cursor.fetchone()

            if user and check_password_hash(user[1], password):
                session['user_id'] = user[0]
                session['patient_id'] = user[2]
                return redirect(url_for('dashboard'))

            flash('Invalid username or password')
        except Exception:
            logger.exception("Login error")
            flash('Login failed. Please try again.')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Flexible: select all columns to handle schema with/without extra fields
        cursor.execute("SELECT * FROM Patients WHERE user_id = ?", (session['user_id'],))
        row = cursor.fetchone()
        if not row:
            flash('Patient profile not found.', 'error')
            return redirect(url_for('logout'))

        # Map row -> dict with lowercase keys
        cols = [desc[0].lower() for desc in cursor.description]
        patient_row = dict(zip(cols, row))

        # Normalize keys for template (keys will exist even if None)
        patient = {
            'patient_id': patient_row.get('patient_id'),
            'name': patient_row.get('name'),
            'age': patient_row.get('age'),
            'gender': patient_row.get('gender'),
            'height': patient_row.get('height'),
            'weight': patient_row.get('weight'),
            'blood_type': patient_row.get('blood_type'),
        }

        # BMI only if height/weight present and valid
        bmi_val = None
        h = patient.get('height')
        w = patient.get('weight')
        try:
            if h is not None and w is not None and float(h) > 0:
                bmi_val = round(float(w) / (float(h) ** 2), 2)
        except Exception:
            bmi_val = None

        # Load predictions
        cursor.execute("""
            SELECT p.prediction_id, p.prediction_date, d.disease_name, p.probability
            FROM Predictions p
            JOIN Diseases d ON p.disease_id = d.disease_id
            WHERE p.patient_id = ?
            ORDER BY p.prediction_date DESC
        """, (patient['patient_id'],))
        predictions = cursor.fetchall()

        return render_template('dashboard.html', patient=patient, bmi=bmi_val, predictions=predictions)

    except Exception as e:
        # Debug ke liye message dikha do (baad me 'e' hata sakte ho)
        logger.exception("Dashboard error")
        flash(f'Error loading dashboard: {e}', 'error')
        return redirect(url_for('login'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/check_symptoms', methods=['GET', 'POST'])
def check_symptoms():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        if request.method == 'POST':
            selected_symptoms = request.form.getlist('symptoms[]')

            if not selected_symptoms:
                flash('Please select at least one symptom')
                return redirect(url_for('check_symptoms'))

            cursor.execute("SELECT patient_id FROM Patients WHERE user_id = ?", 
                           (session['user_id'],))
            patient = cursor.fetchone()
            if not patient:
                flash('Patient not found.')
                return redirect(url_for('dashboard'))

            prediction = predict_disease(selected_symptoms, cursor)

            if prediction['disease_id']:
                cursor.execute("""
                    INSERT INTO Predictions (patient_id, disease_id, probability)
                    VALUES (?, ?, ?)
                """, (patient[0], prediction['disease_id'], prediction['probability']))
                conn.commit()

            return render_template('result.html', prediction=prediction)

        # GET: load symptoms
        cursor.execute("SELECT symptom_id, symptom_name FROM Symptoms ORDER BY symptom_name")
        symptoms = cursor.fetchall()

        return render_template('check_symptoms.html', symptoms=symptoms)

    except Exception:
        logger.exception("Symptom check error")
        flash('Error checking symptoms')
        return redirect(url_for('dashboard'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def predict_disease(symptoms, cursor):
    try:
        cursor.execute("""
            SELECT d.disease_id, d.disease_name, s.symptom_name
            FROM Diseases d
            JOIN Disease_Symptoms ds ON d.disease_id = ds.disease_id
            JOIN Symptoms s ON ds.symptom_id = s.symptom_id
        """)
        rows = cursor.fetchall()

        disease_symptoms = {}
        for row in rows:
            disease_id = row[0]
            disease_name = row[1]
            symptom = row[2]
            if disease_id not in disease_symptoms:
                disease_symptoms[disease_id] = {
                    'name': disease_name,
                    'symptoms': set()
                }
            disease_symptoms[disease_id]['symptoms'].add(symptom)

        best_match = {
            'disease_id': None,
            'disease_name': 'Unknown',
            'probability': 0.0,
            'matched_symptoms': [],
            'alternative_diseases': [],
            'recommendation': "Low probability match. Monitor symptoms and consult a doctor if they persist or worsen.",
            'urgency_level': 'low'
        }

        symptoms_set = set(symptoms)

        for disease_id, disease_info in disease_symptoms.items():
            disease_symptom_set = disease_info['symptoms']
            matched_symptoms = symptoms_set.intersection(disease_symptom_set)

            if len(disease_symptom_set) > 0:
                probability = (len(matched_symptoms) / len(disease_symptom_set)) * 100

                if probability > best_match['probability']:
                    best_match['disease_id'] = disease_id
                    best_match['disease_name'] = disease_info['name']
                    best_match['probability'] = round(probability, 2)
                    best_match['matched_symptoms'] = list(matched_symptoms)

        alternative_diseases = []
        for disease_id, disease_info in disease_symptoms.items():
            if disease_id != best_match['disease_id']:
                matched = symptoms_set.intersection(disease_info['symptoms'])
                probability = (len(matched) / len(disease_info['symptoms'])) * 100 if len(disease_info['symptoms']) else 0
                if probability >= 30:
                    alternative_diseases.append({
                        'name': disease_info['name'],
                        'probability': round(probability, 2)
                    })

        alternative_diseases.sort(key=lambda x: x['probability'], reverse=True)
        best_match['alternative_diseases'] = alternative_diseases[:3]

        if best_match['probability'] > 75:
            best_match['recommendation'] = "High probability of this condition. Please consult a healthcare provider soon."
            best_match['urgency_level'] = 'high'
        elif best_match['probability'] > 50:
            best_match['recommendation'] = "Moderate likelihood. Monitor symptoms and consult a doctor if they worsen."
            best_match['urgency_level'] = 'medium'
        else:
            best_match['recommendation'] = "Low probability match. Monitor your symptoms."
            best_match['urgency_level'] = 'low'

        return best_match

    except Exception:
        logger.exception("Prediction error")
        return {
            'disease_id': None,
            'disease_name': 'Error in prediction',
            'probability': 0,
            'matched_symptoms': [],
            'alternative_diseases': [],
            'recommendation': 'Unable to make prediction. Please try again.',
            'urgency_level': 'low'
        }


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
