USE diseasedetectiondb;
GO

-- Create Tables
CREATE TABLE Users (
    user_id INT PRIMARY KEY IDENTITY(1,1),
    username VARCHAR(50) UNIQUE,
    password VARCHAR(255),
    email VARCHAR(100),
    created_at DATETIME DEFAULT GETDATE()
);

CREATE TABLE Patients (
    patient_id INT PRIMARY KEY IDENTITY(1,1),
    user_id INT,
    name VARCHAR(100),
    age INT,
    gender VARCHAR(10),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE Symptoms (
    symptom_id INT PRIMARY KEY IDENTITY(1,1),
    symptom_name VARCHAR(100) UNIQUE
);

CREATE TABLE Diseases (
    disease_id INT PRIMARY KEY IDENTITY(1,1),
    disease_name VARCHAR(100) UNIQUE,
    description TEXT
);

CREATE TABLE Disease_Symptoms (
    disease_id INT,
    symptom_id INT,
    FOREIGN KEY (disease_id) REFERENCES Diseases(disease_id),
    FOREIGN KEY (symptom_id) REFERENCES Symptoms(symptom_id),
    -- Add a primary key constraint to prevent duplicate entries
    PRIMARY KEY (disease_id, symptom_id)
);

CREATE TABLE Predictions (
    prediction_id INT PRIMARY KEY IDENTITY(1,1),
    patient_id INT,
    disease_id INT,
    prediction_date DATETIME DEFAULT GETDATE(),
    probability DECIMAL(5,2),
    FOREIGN KEY (patient_id) REFERENCES Patients(patient_id),
    FOREIGN KEY (disease_id) REFERENCES Diseases(disease_id)
);

-- Clear existing data
DELETE FROM Predictions;
DELETE FROM Disease_Symptoms;
DELETE FROM Diseases;
DELETE FROM Symptoms;

-- Insert Symptoms
INSERT INTO Symptoms (symptom_name) VALUES 
('Fever'),
('Cough'),
('Headache'),
('Fatigue'),
('Sore Throat'),
('Body Ache'),
('Nausea'),
('Dizziness'),
('Chest Pain'),
('Shortness of Breath'),
('Runny Nose'),
('Sneezing'),
('Loss of Taste'),
('Loss of Smell'),
('Muscle Pain'),
('Joint Pain'),
('Chills'),
('Sweating'),
('Vomiting'),
('Diarrhea');

-- Insert Diseases with detailed descriptions
INSERT INTO Diseases (disease_name, description) VALUES 
('Common Cold', 'A viral infection of the upper respiratory tract causing runny nose, sneezing, and mild fatigue. Usually mild and self-limiting.'),
('Influenza', 'A viral infection causing high fever, body aches, fatigue, and respiratory symptoms. More severe than common cold.'),
('COVID-19', 'A coronavirus infection affecting the respiratory system, notable for loss of taste/smell and varying severity of symptoms.'),
('Migraine', 'A severe headache condition often accompanied by sensitivity to light, nausea, and visual disturbances.'),
('Bronchitis', 'Inflammation of the bronchial tubes causing persistent cough and chest discomfort.'),
('Pneumonia', 'Infection causing inflammation of air sacs in lungs, leading to breathing difficulties and chest pain.'),
('Gastroenteritis', 'Inflammation of the digestive system causing nausea, vomiting, and diarrhea.'),
('Sinusitis', 'Inflammation of the sinuses causing facial pain, headache, and nasal congestion.');

-- Insert Disease-Symptom Relationships with more comprehensive mapping
INSERT INTO Disease_Symptoms (disease_id, symptom_id)
SELECT d.disease_id, s.symptom_id
FROM Diseases d, Symptoms s
WHERE 
    -- Common Cold symptoms
    (d.disease_name = 'Common Cold' AND s.symptom_name IN 
        ('Runny Nose', 'Sneezing', 'Sore Throat', 'Cough', 'Fatigue')) OR
    
    -- Influenza symptoms
    (d.disease_name = 'Influenza' AND s.symptom_name IN 
        ('Fever', 'Body Ache', 'Fatigue', 'Cough', 'Headache', 'Chills', 'Muscle Pain')) OR
    
    -- COVID-19 symptoms
    (d.disease_name = 'COVID-19' AND s.symptom_name IN 
        ('Fever', 'Cough', 'Fatigue', 'Loss of Taste', 'Loss of Smell', 'Shortness of Breath', 'Body Ache')) OR
    
    -- Migraine symptoms
    (d.disease_name = 'Migraine' AND s.symptom_name IN 
        ('Headache', 'Nausea', 'Dizziness', 'Vomiting')) OR
    
    -- Bronchitis symptoms
    (d.disease_name = 'Bronchitis' AND s.symptom_name IN 
        ('Cough', 'Chest Pain', 'Shortness of Breath', 'Fatigue', 'Fever')) OR
    
    -- Pneumonia symptoms
    (d.disease_name = 'Pneumonia' AND s.symptom_name IN 
        ('Fever', 'Cough', 'Shortness of Breath', 'Chest Pain', 'Fatigue', 'Sweating')) OR
    
    -- Gastroenteritis symptoms
    (d.disease_name = 'Gastroenteritis' AND s.symptom_name IN 
        ('Nausea', 'Vomiting', 'Diarrhea', 'Fever', 'Body Ache')) OR
    
    -- Sinusitis symptoms
    (d.disease_name = 'Sinusitis' AND s.symptom_name IN 
        ('Headache', 'Runny Nose', 'Sore Throat', 'Fever', 'Fatigue'));

-- Useful queries for checking data
GO

-- Check all symptoms
SELECT * FROM Symptoms ORDER BY symptom_id;

-- Check all diseases
SELECT * FROM Diseases ORDER BY disease_id;

-- Check symptoms for each disease
SELECT 
    d.disease_name,
    STRING_AGG(s.symptom_name, ', ') as symptoms
FROM Diseases d
JOIN Disease_Symptoms ds ON d.disease_id = ds.disease_id
JOIN Symptoms s ON ds.symptom_id = s.symptom_id
GROUP BY d.disease_name
ORDER BY d.disease_name;

-- Check predictions with patient details
SELECT 
    p.name as patient_name,
    d.disease_name,
    pr.probability,
    FORMAT(pr.prediction_date, 'yyyy-MM-dd HH:mm') as prediction_date
FROM Predictions pr
JOIN Patients p ON pr.patient_id = p.patient_id
JOIN Diseases d ON pr.disease_id = d.disease_id
ORDER BY pr.prediction_date DESC;