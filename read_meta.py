#!/usr/bin/env python3
import sys, json
from PIL import Image, IptcImagePlugin
import piexif

filepath = sys.argv[1]

# Kultaisen leikkauksen kohdat ruudussa (johon haluamme kasvot/pään)
GOLDEN_X = 0.382   # vaaka: hieman vasemmalle
GOLDEN_Y = 0.382   # pysty: hieman ylös

def find_subject(img_cv, w, h):
    """
    Yrittää löytää subjektin järjestyksessä:
    1. Frontaalikasvo (3 cascadea + CLAHE)
    2. Profiilikasvot
    3. Silmät (pään arviointi silmien kautta)
    4. Yläruumis (pään yläosa arvioitu)
    Palauttaa (center_x_pct, center_y_pct) tai None
    """
    import cv2
    import numpy as np

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))
    gray_eq = clahe.apply(gray)
    min_size = (int(min(w,h)*0.04), int(min(w,h)*0.04))

    # 1. Frontaalikasvo
    for cf in ['haarcascade_frontalface_alt.xml',
               'haarcascade_frontalface_default.xml',
               'haarcascade_frontalface_alt2.xml']:
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + cf)
        for src in [gray_eq, gray]:
            faces = cascade.detectMultiScale(src, scaleFactor=1.05,
                        minNeighbors=3, minSize=min_size)
            if len(faces) > 0:
                fx, fy, fw, fh = max(faces, key=lambda f: f[2]*f[3])
                # Kasvojen otsakohta — 25% alaspäin kasvoista
                cx = (fx + fw * 0.5) / w
                cy = (fy + fh * 0.25) / h
                return cx, cy, 'face'

    # 2. Profiilikasvot
    for src in [gray_eq, gray]:
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_profileface.xml')
        faces = cascade.detectMultiScale(src, scaleFactor=1.05,
                    minNeighbors=3, minSize=min_size)
        if len(faces) > 0:
            fx, fy, fw, fh = max(faces, key=lambda f: f[2]*f[3])
            cx = (fx + fw * 0.5) / w
            cy = (fy + fh * 0.25) / h
            return cx, cy, 'profile'

    # 3. Silmät — pään sijainti arvioidaan silmien yläpuolelta
    for cf in ['haarcascade_eye_tree_eyeglasses.xml', 'haarcascade_eye.xml']:
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + cf)
        for src in [gray_eq, gray]:
            eyes = cascade.detectMultiScale(src, scaleFactor=1.05,
                        minNeighbors=3, minSize=(int(min(w,h)*0.02),)*2)
            if len(eyes) >= 1:
                # Käytä ylintä silmäparia tai yksittäistä silmää
                top_eye = min(eyes, key=lambda e: e[1])
                ex, ey, ew, eh = top_eye
                cx = (ex + ew * 0.5) / w
                # Pää on silmien yläpuolella — arvioidaan 1.5x silmän korkeus
                cy = max(0.02, (ey - eh * 1.5) / h)
                return cx, cy, 'eyes'

    # 4. Yläruumis — pään arviointi yläreunasta
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_upperbody.xml')
    for src in [gray_eq, gray]:
        bodies = cascade.detectMultiScale(src, scaleFactor=1.05,
                    minNeighbors=4, minSize=(int(min(w,h)*0.1),)*2)
        if len(bodies) > 0:
            bx, by, bw, bh = max(bodies, key=lambda b: b[2]*b[3])
            cx = (bx + bw * 0.5) / w
            # Pää on yläruumiin yläosassa — n. 15% alaspäin
            cy = (by + bh * 0.15) / h
            return cx, cy, 'body'

    return None, None, None

def calc_object_position(subject_x, subject_y, orientation):
    """
    Pystykuville: palauttaa vain Y-aseman (X = center).
    Vaakakuville: ei käytetä lainkaan.
    """
    # Siirretään subjekti kultaisen leikkauksen Y-kohtaan (38%)
    raw_y = subject_y - GOLDEN_Y + 0.38
    pos_y = max(2, min(60, round(raw_y * 100)))
    return f"center {pos_y}%"

try:
    img = Image.open(filepath)

    # IPTC
    iptc = IptcImagePlugin.getiptcinfo(img) or {}
    kw_raw = iptc.get((2,25), [])
    if isinstance(kw_raw, bytes):
        kw_raw = [kw_raw]
    keywords = [k.decode('utf-8','ignore').strip() for k in kw_raw if k]

    date_raw = iptc.get((2,55), b'').decode('utf-8','ignore').strip()
    iso_date = None
    if len(date_raw) == 8:
        iso_date = date_raw[:4]+'-'+date_raw[4:6]+'-'+date_raw[6:8]

    if not iso_date:
        try:
            exif = piexif.load(img.info.get('exif', b''))
            dt = exif.get('Exif',{}).get(36867) or exif.get('0th',{}).get(306)
            if dt:
                iso_date = dt.decode('utf-8','ignore')[:10].replace(':','-')
        except:
            pass

    artist = next((k for k in keywords if not k.startswith('http')), None)
    all_keywords = [k for k in keywords if not k.startswith('http')]

    w, h = img.size
    orientation = 'portrait' if h > w else 'landscape'

    # Kasvojentunnistus
    face_position = None
    try:
        import cv2
        import numpy as np

        img_cv = cv2.imread(filepath)
        if img_cv is not None:
            sx, sy, method = find_subject(img_cv, w, h)
            if sx is not None and orientation == 'portrait':
                face_position = calc_object_position(sx, sy, orientation)
                sys.stderr.write(f'  [{method}] subject at {sx:.2f},{sy:.2f} → {face_position}\n')
            elif orientation == 'portrait':
                # Fallback pystykuville jos ei löydy subjektia
                face_position = "50% 15%"
                sys.stderr.write(f'  [fallback] no subject found\n')
    except Exception as e:
        face_position = "50% 15%" if orientation == 'portrait' else None
        sys.stderr.write(f'  [error] {e}\n')

    print(json.dumps({
        'date':         iso_date,
        'artist':       artist,
        'keywords':     all_keywords,
        'orientation':  orientation,
        'width':        w,
        'height':       h,
        'facePosition': face_position,
    }))

except Exception as e:
    print(json.dumps({
        'date':None,'artist':None,'keywords':[],
        'orientation':'landscape','width':0,'height':0,
        'facePosition':None
    }))
    sys.stderr.write(str(e)+'\n')
