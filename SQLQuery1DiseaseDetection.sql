/* ============================
   Clean, simple schema for your app
   WARNING: Drops old tables. Take backup if needed.
   ============================ */

IF DB_ID(N'diseasedetectiondb') IS NULL
BEGIN
    CREATE DATABASE diseasedetectiondb;
END
GO

USE diseasedetectiondb;
GO

/* Drop views if exist */
IF OBJECT_ID('dbo.v_DiseaseSymptoms', 'V') IS NOT NULL DROP VIEW dbo.v_DiseaseSymptoms;
IF OBJECT_ID('dbo.v_PredictionsWithDetails', 'V') IS NOT NULL DROP VIEW dbo.v_PredictionsWithDetails;
GO

/* Drop tables in dependency order */
IF OBJECT_ID('dbo.Predictions', 'U') IS NOT NULL DROP TABLE dbo.Predictions;
IF OBJECT_ID('dbo.Disease_Symptoms', 'U') IS NOT NULL DROP TABLE dbo.Disease_Symptoms;
IF OBJECT_ID('dbo.Patients', 'U') IS NOT NULL DROP TABLE dbo.Patients;
IF OBJECT_ID('dbo.Diseases', 'U') IS NOT NULL DROP TABLE dbo.Diseases;
IF OBJECT_ID('dbo.Symptoms', 'U') IS NOT NULL DROP TABLE dbo.Symptoms;
IF OBJECT_ID('dbo.Users', 'U') IS NOT NULL DROP TABLE dbo.Users;
GO

/* ============================
   Tables
   ============================ */

/* Users */
CREATE TABLE dbo.Users (
    user_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    username NVARCHAR(50) NOT NULL UNIQUE,
    password NVARCHAR(255) NOT NULL,
    email NVARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);
GO

/* Patients (1:1 with Users) */
CREATE TABLE dbo.Patients (
    patient_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    name NVARCHAR(100) NOT NULL,
    age INT NOT NULL,
    gender NVARCHAR(10) NOT NULL,
    height FLOAT NULL,            -- meters (e.g., 1.75)
    weight FLOAT NULL,            -- kg (e.g., 68.5)
    blood_type NVARCHAR(5) NOT NULL, -- e.g., A+, O-, AB+
    CONSTRAINT FK_Patients_Users
        FOREIGN KEY (user_id) REFERENCES dbo.Users(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT CK_Patients_Age CHECK (age BETWEEN 0 AND 130),
    CONSTRAINT CK_Patients_Gender CHECK (gender IN (N'male', N'female', N'other')),
    CONSTRAINT CK_Patients_Height CHECK (height IS NULL OR height > 0),
    CONSTRAINT CK_Patients_Weight CHECK (weight IS NULL OR weight > 0),
    CONSTRAINT CK_Patients_BloodType CHECK (blood_type IN (N'A+',N'A-',N'B+',N'B-',N'O+',N'O-',N'AB+',N'AB-'))
);
GO

/* Symptoms master */
CREATE TABLE dbo.Symptoms (
    symptom_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    symptom_name NVARCHAR(100) NOT NULL UNIQUE
);
GO

/* Diseases master */
CREATE TABLE dbo.Diseases (
    disease_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    disease_name NVARCHAR(100) NOT NULL UNIQUE,
    description NVARCHAR(MAX) NULL
);
GO

/* Disease <-> Symptoms (many-to-many) */
CREATE TABLE dbo.Disease_Symptoms (
    disease_id INT NOT NULL,
    symptom_id INT NOT NULL,
    CONSTRAINT PK_Disease_Symptoms PRIMARY KEY (disease_id, symptom_id),
    CONSTRAINT FK_DS_Diseases FOREIGN KEY (disease_id) 
        REFERENCES dbo.Diseases(disease_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT FK_DS_Symptoms FOREIGN KEY (symptom_id) 
        REFERENCES dbo.Symptoms(symptom_id) ON DELETE CASCADE ON UPDATE CASCADE
);
GO

/* Predictions history */
CREATE TABLE dbo.Predictions (
    prediction_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    patient_id INT NOT NULL,
    disease_id INT NOT NULL,
    prediction_date DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    probability DECIMAL(5,2) NOT NULL,
    CONSTRAINT FK_Pred_Patient FOREIGN KEY (patient_id) 
        REFERENCES dbo.Patients(patient_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT FK_Pred_Disease FOREIGN KEY (disease_id) 
        REFERENCES dbo.Diseases(disease_id) ON DELETE CASCADE ON UPDATE CASCADE
);
GO

/* Helpful indexes */
CREATE INDEX IX_Predictions_PatientDate ON dbo.Predictions(patient_id, prediction_date DESC);
CREATE INDEX IX_DS_Symptom ON dbo.Disease_Symptoms(symptom_id);
GO

/* ============================
   Seed Data
   ============================ */

/* Symptoms */
INSERT INTO dbo.Symptoms (symptom_name) VALUES 
(N'Fever'),
(N'Cough'),
(N'Headache'),
(N'Fatigue'),
(N'Sore Throat'),
(N'Body Ache'),
(N'Nausea'),
(N'Dizziness'),
(N'Chest Pain'),
(N'Shortness of Breath'),
(N'Runny Nose'),
(N'Sneezing'),
(N'Loss of Taste'),
(N'Loss of Smell'),
(N'Muscle Pain'),
(N'Joint Pain'),
(N'Chills'),
(N'Sweating'),
(N'Vomiting'),
(N'Diarrhea');
GO

/* Diseases */
INSERT INTO dbo.Diseases (disease_name, description) VALUES 
(N'Common Cold', N'A viral infection of the upper respiratory tract causing runny nose, sneezing, and mild fatigue. Usually mild and self-limiting.'),
(N'Influenza', N'A viral infection causing high fever, body aches, fatigue, and respiratory symptoms. More severe than common cold.'),
(N'COVID-19', N'A coronavirus infection affecting the respiratory system, notable for loss of taste/smell and varying severity of symptoms.'),
(N'Migraine', N'A severe headache condition often accompanied by sensitivity to light, nausea, and visual disturbances.'),
(N'Bronchitis', N'Inflammation of the bronchial tubes causing persistent cough and chest discomfort.'),
(N'Pneumonia', N'Infection causing inflammation of air sacs in lungs, leading to breathing difficulties and chest pain.'),
(N'Gastroenteritis', N'Inflammation of the digestive system causing nausea, vomiting, and diarrhea.'),
(N'Sinusitis', N'Inflammation of the sinuses causing facial pain, headache, and nasal congestion.');
GO

/* Disease ↔ Symptoms mapping */
INSERT INTO dbo.Disease_Symptoms (disease_id, symptom_id)
SELECT d.disease_id, s.symptom_id
FROM dbo.Diseases d
CROSS JOIN dbo.Symptoms s
WHERE 
    (d.disease_name = N'Common Cold'    AND s.symptom_name IN (N'Runny Nose', N'Sneezing', N'Sore Throat', N'Cough', N'Fatigue')) OR
    (d.disease_name = N'Influenza'      AND s.symptom_name IN (N'Fever', N'Body Ache', N'Fatigue', N'Cough', N'Headache', N'Chills', N'Muscle Pain')) OR
    (d.disease_name = N'COVID-19'       AND s.symptom_name IN (N'Fever', N'Cough', N'Fatigue', N'Loss of Taste', N'Loss of Smell', N'Shortness of Breath', N'Body Ache')) OR
    (d.disease_name = N'Migraine'       AND s.symptom_name IN (N'Headache', N'Nausea', N'Dizziness', N'Vomiting')) OR
    (d.disease_name = N'Bronchitis'     AND s.symptom_name IN (N'Cough', N'Chest Pain', N'Shortness of Breath', N'Fatigue', N'Fever')) OR
    (d.disease_name = N'Pneumonia'      AND s.symptom_name IN (N'Fever', N'Cough', N'Shortness of Breath', N'Chest Pain', N'Fatigue', N'Sweating')) OR
    (d.disease_name = N'Gastroenteritis'AND s.symptom_name IN (N'Nausea', N'Vomiting', N'Diarrhea', N'Fever', N'Body Ache')) OR
    (d.disease_name = N'Sinusitis'      AND s.symptom_name IN (N'Headache', N'Runny Nose', N'Sore Throat', N'Fever', N'Fatigue'));
GO

/* ============================
   Helpful Views
   ============================ */

CREATE VIEW dbo.v_DiseaseSymptoms AS
SELECT 
    d.disease_id,
    d.disease_name,
    STRING_AGG(s.symptom_name, N', ') WITHIN GROUP (ORDER BY s.symptom_name) AS symptoms
FROM dbo.Diseases d
JOIN dbo.Disease_Symptoms ds ON d.disease_id = ds.disease_id
JOIN dbo.Symptoms s ON ds.symptom_id = s.symptom_id
GROUP BY d.disease_id, d.disease_name;
GO

CREATE VIEW dbo.v_PredictionsWithDetails AS
SELECT 
    pr.prediction_id,
    pr.prediction_date,
    pr.probability,
    p.patient_id,
    p.name AS patient_name,
    d.disease_id,
    d.disease_name
FROM dbo.Predictions pr
JOIN dbo.Patients p ON pr.patient_id = p.patient_id
JOIN dbo.Diseases d ON pr.disease_id = d.disease_id;
GO

/* ============================
   Quick checks (run anytime)
   ============================ */

-- Counts
SELECT 'Users' AS [table], COUNT(*) AS [rows] FROM dbo.Users
UNION ALL SELECT 'Patients', COUNT(*) FROM dbo.Patients
UNION ALL SELECT 'Symptoms', COUNT(*) FROM dbo.Symptoms
UNION ALL SELECT 'Diseases', COUNT(*) FROM dbo.Diseases
UNION ALL SELECT 'Disease_Symptoms', COUNT(*) FROM dbo.Disease_Symptoms
UNION ALL SELECT 'Predictions', COUNT(*) FROM dbo.Predictions;

-- All symptoms
SELECT * FROM dbo.Symptoms ORDER BY symptom_id;

-- All diseases
SELECT * FROM dbo.Diseases ORDER BY disease_id;

-- Diseases with their symptom list
SELECT * FROM dbo.v_DiseaseSymptoms ORDER BY disease_name;

-- Predictions with patient details
SELECT * FROM dbo.v_PredictionsWithDetails ORDER BY prediction_date DESC;

/* To inspect one user after registering (replace values):
-- Find user_id
SELECT * FROM dbo.Users WHERE username = N'your_username';
SELECT * FROM dbo.Patients WHERE user_id = <that_user_id>;
*/
