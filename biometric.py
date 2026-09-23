# biometric.py
# Simple face-based biometric verification for the SACCO system.
#
# Uses OpenCV's built-in LBPH (Local Binary Patterns Histogram) face
# recognizer. This needs a webcam but NO fingerprint hardware and no
# extra heavy dependencies like dlib.
#
# Install requirement:
#   pip install opencv-contrib-python
#
# (Plain "opencv-python" does NOT include cv2.face — you need the
#  "contrib" package, or this will fail with an AttributeError.)

import os
import json

try:
    import cv2
except ImportError:
    cv2 = None

# Where biometric data is stored, separate from the main sacco JSON file
BIOMETRIC_DIR = "biometric_data"
SAMPLES_DIR = os.path.join(BIOMETRIC_DIR, "samples")
MODEL_PATH = os.path.join(BIOMETRIC_DIR, "model.yml")
LABELS_PATH = os.path.join(BIOMETRIC_DIR, "labels.json")

# How many face photos to capture during enrollment
SAMPLES_PER_MEMBER = 20

# LBPH prediction returns a "confidence" score where LOWER = better match.
# Anything above this is treated as "not the same person".
CONFIDENCE_THRESHOLD = 70

# How many live attempts a member gets before verification fails
MAX_VERIFY_ATTEMPTS = 3


def _check_cv2():
    """Make sure OpenCV (with the contrib face module) is available."""
    if cv2 is None:
        print("\nOpenCV is not installed. Run: pip install opencv-contrib-python")
        return False
    if not hasattr(cv2, "face"):
        print("\nYour OpenCV install is missing the 'face' module.")
        print("Run: pip uninstall opencv-python  (if installed)")
        print("Then: pip install opencv-contrib-python")
        return False
    return True


def _ensure_dirs():
    os.makedirs(SAMPLES_DIR, exist_ok=True)


def _load_labels():
    """labels.json maps a numeric label (needed by LBPH) to a member_id."""
    if not os.path.exists(LABELS_PATH):
        return {}
    with open(LABELS_PATH, "r") as f:
        return json.load(f)


def _save_labels(labels):
    with open(LABELS_PATH, "w") as f:
        json.dump(labels, f, indent=2)


def _get_face_cascade():
    """
    Load the Haar cascade for face detection.

    We ship our own copy of haarcascade_frontalface_default.xml next to
    this file, because some OpenCV pip packages (depending on version/
    platform) don't reliably place their bundled data files where
    cv2.data.haarcascades points. Using our own local copy avoids that
    entirely. If for some reason it's missing, we fall back to asking
    OpenCV for its own copy.
    """
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "haarcascade_frontalface_default.xml")

    cascade = cv2.CascadeClassifier(local_path)
    if not cascade.empty():
        return cascade

    # Fall back to whatever OpenCV itself thinks its data path is
    fallback_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(fallback_path)
    if cascade.empty():
        print("\nCould not load the face detection model from either:")
        print("  " + local_path)
        print("  " + fallback_path)
        print("Make sure haarcascade_frontalface_default.xml is in the same folder as biometric.py.")
    return cascade


def _detect_face(gray_frame, cascade):
    """Return the largest detected face region as (x, y, w, h), or None."""
    faces = cascade.detectMultiScale(gray_frame, scaleFactor=1.2, minNeighbors=5, minSize=(120, 120))
    if len(faces) == 0:
        return None
    # Pick the largest face in frame (in case of a busy background)
    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    return faces[0]


def enroll_face(member_id):
    """
    Capture face samples for a member using the webcam and (re)train
    the shared face recognition model. Returns True on success.
    """
    if not _check_cv2():
        return False

    _ensure_dirs()
    member_dir = os.path.join(SAMPLES_DIR, member_id)
    os.makedirs(member_dir, exist_ok=True)

    cascade = _get_face_cascade()
    if cascade.empty():
        return False

    cam = cv2.VideoCapture(0)

    if not cam.isOpened():
        print("\nCould not access the webcam. Is it connected and not in use?")
        return False

    print("\nLook at the camera. Capturing " + str(SAMPLES_PER_MEMBER) + " samples.")
    print("Move your head slightly between shots for a better model.")
    print("Press 'q' at any time to cancel.\n")

    count = 0
    while count < SAMPLES_PER_MEMBER:
        ok, frame = cam.read()
        if not ok:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face = _detect_face(gray, cascade)

        if face is not None:
            x, y, w, h = face
            face_img = gray[y:y + h, x:x + w]
            face_img = cv2.resize(face_img, (200, 200))
            count += 1
            cv2.imwrite(os.path.join(member_dir, str(count) + ".png"), face_img)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, "Captured " + str(count) + "/" + str(SAMPLES_PER_MEMBER),
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow("Enroll Biometric - press q to cancel", frame)
        if cv2.waitKey(200) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()

    if count < SAMPLES_PER_MEMBER:
        print("\nEnrollment cancelled or incomplete (" + str(count) + " samples captured).")
        return False

    print("\nSamples captured. Training model...")
    return _retrain_model()


def _retrain_model():
    """Rebuild the LBPH model from every sample currently on disk."""
    if not _check_cv2():
        return False

    labels = {}
    faces = []
    numeric_labels = []
    next_label = 0

    if not os.path.exists(SAMPLES_DIR):
        print("No enrolled members yet.")
        return False

    for member_id in sorted(os.listdir(SAMPLES_DIR)):
        member_dir = os.path.join(SAMPLES_DIR, member_id)
        if not os.path.isdir(member_dir):
            continue

        labels[str(next_label)] = member_id

        for filename in os.listdir(member_dir):
            path = os.path.join(member_dir, filename)
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                faces.append(img)
                numeric_labels.append(next_label)

        next_label += 1

    if len(faces) == 0:
        print("No face samples found to train on.")
        return False

    import numpy as np
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(numeric_labels))

    _ensure_dirs()
    recognizer.save(MODEL_PATH)
    _save_labels(labels)

    print("Biometric model trained on " + str(len(labels)) + " member(s).")
    return True


def is_enrolled(member_id):
    """Check whether a member already has face samples on disk."""
    member_dir = os.path.join(SAMPLES_DIR, member_id)
    return os.path.isdir(member_dir) and len(os.listdir(member_dir)) > 0


def verify_face(member_id):
    """
    Ask the member to look at the camera and confirm it matches the
    face on file for member_id. Returns True if verified, False otherwise.
    """
    if not _check_cv2():
        return False

    if not os.path.exists(MODEL_PATH) or not is_enrolled(member_id):
        print("\nThis member has not enrolled a biometric yet.")
        return False

    labels = _load_labels()
    # Reverse lookup: member_id -> numeric label
    expected_label = None
    for numeric_label, mid in labels.items():
        if mid == member_id:
            expected_label = int(numeric_label)
            break

    if expected_label is None:
        print("\nNo biometric record found for this member.")
        return False

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(MODEL_PATH)

    cascade = _get_face_cascade()
    if cascade.empty():
        return False

    cam = cv2.VideoCapture(0)

    if not cam.isOpened():
        print("\nCould not access the webcam. Is it connected and not in use?")
        return False

    print("\nBiometric verification required. Look at the camera...")
    print("Press 'q' to cancel.\n")

    verified = False
    attempts = 0
    frames_checked = 0

    while attempts < MAX_VERIFY_ATTEMPTS and not verified:
        ok, frame = cam.read()
        if not ok:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face = _detect_face(gray, cascade)

        if face is not None:
            x, y, w, h = face
            face_img = cv2.resize(gray[y:y + h, x:x + w], (200, 200))
            predicted_label, confidence = recognizer.predict(face_img)
            frames_checked += 1

            label_text = "Checking..."
            color = (0, 165, 255)

            if predicted_label == expected_label and confidence <= CONFIDENCE_THRESHOLD:
                verified = True
                label_text = "Verified!"
                color = (0, 255, 0)
            elif frames_checked % 15 == 0:
                # Every so often, count a clear mismatch as a failed attempt
                attempts += 1
                label_text = "No match (attempt " + str(attempts) + "/" + str(MAX_VERIFY_ATTEMPTS) + ")"
                color = (0, 0, 255)

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, label_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        cv2.imshow("Biometric Verification - press q to cancel", frame)
        key = cv2.waitKey(200) & 0xFF
        if key == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()

    if verified:
        print("Biometric verification PASSED.")
    else:
        print("Biometric verification FAILED.")

    return verified