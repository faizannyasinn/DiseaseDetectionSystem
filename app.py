from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = ' '  # Change this to a random secret key

def get_db():
    try:
        conn_str = (
            "Driver={ODBC Driver 17 for SQL Server};"
            "Server=your server name;"
            "Database=diseasedetectiondb;"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
        return pyodbc.connect(conn_str)
    except pyodbc.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            email = request.form['email']
            name = request.form['name']
            age = request.form['age']
            gender = request.form['gender']

            hashed_password = generate_password_hash(password)

            conn = get_db()
            cursor = conn.cursor()

            # Check if username already exists
            cursor.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
            if cursor.fetchone():
                flash('Username already exists!')
                return render_template('register.html')

            # Insert user
            cursor.execute("""
                INSERT INTO Users (username, password, email)
                VALUES (?, ?, ?)
            """, (username, hashed_password, email))
            
            conn.commit()
            
            # Get the user_id
            cursor.execute("SELECT @@IDENTITY")
            user_id = cursor.fetchone()[0]

            # Insert patient
            cursor.execute("""
                INSERT INTO Patients (user_id, name, age, gender)
                VALUES (?, ?, ?, ?)
            """, (user_id, name, age, gender))

            conn.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            flash('Registration failed. Please try again.')
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT Users.user_id, Users.password, Patients.patient_id 
                FROM Users 
                JOIN Patients ON Users.user_id = Patients.user_id 
                WHERE Users.username = ?
            """, (username,))
            
            user = cursor.fetchone()

            if user and check_password_hash(user[1], password):
                session['user_id'] = user[0]
                session['patient_id'] = user[2]
                return redirect(url_for('dashboard'))
            
            flash('Invalid username or password')

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('Login failed. Please try again.')
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Get patient info
        cursor.execute("""
            SELECT * FROM Patients 
            WHERE user_id = ?
        """, (session['user_id'],))
        patient = cursor.fetchone()

        # Get predictions
        cursor.execute("""
            SELECT 
                p.prediction_date,
                d.disease_name,
                p.probability
            FROM Predictions p
            JOIN Diseases d ON p.disease_id = d.disease_id
            WHERE p.patient_id = ?
            ORDER BY p.prediction_date DESC
        """, (patient[0],))
        predictions = cursor.fetchall()

        return render_template('dashboard.html', 
                             patient=patient, 
                             predictions=predictions)

    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        flash('Error loading dashboard')
        return redirect(url_for('login'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
                conn.close()

@app.route('/check_symptoms', methods=['GET', 'POST'])
def check_symptoms():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db()
        cursor = conn.cursor()

        if request.method == 'POST':
            selected_symptoms = request.form.getlist('symptoms[]')
            
            if not selected_symptoms:
                flash('Please select at least one symptom')
                return redirect(url_for('check_symptoms'))

            # Get patient_id
            cursor.execute("SELECT patient_id FROM Patients WHERE user_id = ?", 
                         (session['user_id'],))
            patient = cursor.fetchone()

            # Predict disease
            prediction = predict_disease(selected_symptoms, cursor)
            
            if prediction['disease_id']:
                # Store prediction
                cursor.execute("""
                    INSERT INTO Predictions (patient_id, disease_id, probability)
                    VALUES (?, ?, ?)
                """, (patient[0], prediction['disease_id'], prediction['probability']))
                conn.commit()

            return render_template('result.html', prediction=prediction)

        # Get all symptoms
        cursor.execute("SELECT * FROM Symptoms ORDER BY symptom_name")
        symptoms = cursor.fetchall()
        
        return render_template('check_symptoms.html', symptoms=symptoms)

    except Exception as e:
        logger.error(f"Symptom check error: {str(e)}")
        flash('Error checking symptoms')
        return redirect(url_for('dashboard'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def predict_disease(symptoms, cursor):
    try:
        # First get all diseases and their symptoms
        cursor.execute("""
            SELECT 
                d.disease_id,
                d.disease_name,
                s.symptom_name
            FROM Diseases d
            JOIN Disease_Symptoms ds ON d.disease_id = ds.disease_id
            JOIN Symptoms s ON ds.symptom_id = s.symptom_id
        """)
        
        # Create a dictionary to store disease symptoms
        disease_symptoms = {}
        for row in cursor.fetchall():
            disease_id = row[0]
            disease_name = row[1]
            symptom = row[2]
            
            if disease_id not in disease_symptoms:
                disease_symptoms[disease_id] = {
                    'name': disease_name,
                    'symptoms': set()
                }
            disease_symptoms[disease_id]['symptoms'].add(symptom)

        # Find best matching disease
        best_match = {
            'disease_id': None,
            'disease_name': 'Unknown',
            'probability': 0,
            'matched_symptoms': []
        }

        symptoms_set = set(symptoms)
        
        for disease_id, disease_info in disease_symptoms.items():
            disease_symptom_set = disease_info['symptoms']
            
            # Calculate matching symptoms
            matched_symptoms = symptoms_set.intersection(disease_symptom_set)
            
            # Calculate probability
            if len(disease_symptom_set) > 0:  # Avoid division by zero
                probability = (len(matched_symptoms) / len(disease_symptom_set)) * 100
                
                # Update best match if this is better
                if probability > best_match['probability']:
                    best_match = {
                        'disease_id': disease_id,
                        'disease_name': disease_info['name'],
                        'probability': round(probability, 2),
                        'matched_symptoms': list(matched_symptoms)
                    }

        # Get alternative diseases (other diseases with >30% probability)
        alternative_diseases = []
        for disease_id, disease_info in disease_symptoms.items():
            if disease_id != best_match['disease_id']:
                matched = symptoms_set.intersection(disease_info['symptoms'])
                probability = (len(matched) / len(disease_info['symptoms'])) * 100
                
                if probability >= 30:
                    alternative_diseases.append({
                        'name': disease_info['name'],
                        'probability': round(probability, 2)
                    })

        # Sort alternative diseases by probability
        alternative_diseases.sort(key=lambda x: x['probability'], reverse=True)
        best_match['alternative_diseases'] = alternative_diseases[:3]  # Top 3 alternatives

        # Add recommendation based on probability
        if best_match['probability'] > 75:
            best_match['recommendation'] = "High probability of this condition. Please consult a healthcare provider soon."
            best_match['urgency_level'] = 'high'
        elif best_match['probability'] > 50:
            best_match['recommendation'] = "Moderate likelihood of this condition. Monitor symptoms and consult a doctor if they worsen."
            best_match['urgency_level'] = 'medium'
        else:
            best_match['recommendation'] = "Low probability match. Monitor your symptoms and consult a doctor if they persist or worsen."
            best_match['urgency_level'] = 'low'

        return best_match

    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return {
            'disease_id': None,
            'disease_name': 'Error in prediction',
            'probability': 0,
            'recommendation': 'Unable to make prediction. Please try again.',
            'urgency_level': 'low'
        }

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
