#!/usr/bin/env python3
import sys, json
from PIL import Image, IptcImagePlugin
import piexif

filepath = sys.argv[1]

GOLDEN_Y = 0.382

def find_subject(img_cv, w, h):
    import cv2
    import numpy as np

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    gray_eq = clahe.apply(gray)
    min_size = (int(min(w,h)*0.04), int(min(w,h)*0.04))

    # 1. Frontaalikasvo — kokeile myös pienemmillä arvoilla
    for cf in ['haarcascade_frontalface_alt.xml',
               'haarcascade_frontalface_default.xml',
               'haarcascade_frontalface_alt2.xml']:
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + cf)
        for src in [gray_eq, gray]:
            for neighbors in [3, 2]:
                faces = cascade.detectMultiScale(
                    src, scaleFactor=1.05,
                    minNeighbors=neighbors, minSize=min_size)
                if len(faces) > 0:
                    fx, fy, fw, fh = max(faces, key=lambda f: f[2]*f[3])
                    cx = (fx + fw * 0.5) / w
                    cy = (fy + fh * 0.25) / h
                    return cx, cy, 'face'

    # 2. Profiilikasvot — molemmat suunnat
    cascade_p = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_profileface.xml')
    for src in [gray_eq, gray]:
        faces = cascade_p.detectMultiScale(
            src, scaleFactor=1.05, minNeighbors=2, minSize=min_size)
        if len(faces) > 0:
            fx, fy, fw, fh = max(faces, key=lambda f: f[2]*f[3])
            cx = (fx + fw * 0.5) / w
            cy = (fy + fh * 0.25) / h
            return cx, cy, 'profile'

        # Käännetty kuva profiilille
        flipped = cv2.flip(src, 1)
        faces = cascade_p.detectMultiScale(
            flipped, scaleFactor=1.05, minNeighbors=2, minSize=min_size)
        if len(faces) > 0:
            fx, fy, fw, fh = max(faces, key=lambda f: f[2]*f[3])
            # Käännetään x takaisin
            cx = 1.0 - (fx + fw * 0.5) / w
            cy = (fy + fh * 0.25) / h
            return cx, cy, 'profile_flip'

    # 3. Silmät — pään arviointi
    for cf in ['haarcascade_eye_tree_eyeglasses.xml', 'haarcascade_eye.xml']:
        cascade_e = cv2.CascadeClassifier(cv2.data.haarcascades + cf)
        for src in [gray_eq, gray]:
            eyes = cascade_e.detectMultiScale(
                src, scaleFactor=1.05, minNeighbors=2,
                minSize=(int(min(w,h)*0.02),)*2)
            if len(eyes) >= 1:
                top_eye = min(eyes, key=lambda e: e[1])
                ex, ey, ew, eh = top_eye
                cx = (ex + ew * 0.5) / w
                cy = max(0.02, (ey - eh * 2.0) / h)
                return cx, cy, 'eyes'

    # 4. Yläruumis
    cascade_b = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_upperbody.xml')
    for src in [gray_eq, gray]:
        bodies = cascade_b.detectMultiScale(
            src, scaleFactor=1.05, minNeighbors=3,
            minSize=(int(min(w,h)*0.1),)*2)
        if len(bodies) > 0:
            bx, by, bw, bh = max(bodies, key=lambda b: b[2]*b[3])
            cx = (bx + bw * 0.5) / w
            cy = max(0.01, (by + bh * 0.1) / h)
            return cx, cy, 'body'

    return None, None, None

def calc_position(sy, h):
    """Laske Y object-position niin että subjekti on kultaisessa leikkauksessa"""
    # Haluamme subjektin ruudussa kohdassa GOLDEN_Y (38%)
    # Jos subjekti on kuvassa kohdassa sy ja kuva on h px korkea
    # ja container on esim. 100vh, niin:
    # object-position Y% siirtää kuvaa: 0%=ylhäältä, 100%=alhaalta
    # Lasketaan: kuinka paljon pitää siirtää jotta sy on kohdassa GOLDEN_Y ruudussa
    pos_y = max(2, min(65, round(sy * 100 - GOLDEN_Y * 30)))
    return pos_y

try:
    img = Image.open(filepath)

    iptc = IptcImagePlugin.getiptcinfo(img) or {}
    kw_raw = iptc.get((2,25), [])
    if isinstance(kw_raw, bytes): kw_raw = [kw_raw]
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
        except: pass

    artist = next((k for k in keywords if not k.startswith('http')), None)
    all_keywords = [k for k in keywords if not k.startswith('http')]

    w, h = img.size
    orientation = 'portrait' if h > w else 'landscape'

    face_position = None
    if orientation == 'portrait':
        try:
            import cv2
            img_cv = cv2.imread(filepath)
            if img_cv is not None:
                sx, sy, method = find_subject(img_cv, w, h)
                if sx is not None:
                    pos_y = calc_position(sy, h)
                    face_position = f"center {pos_y}%"
                    sys.stderr.write(f'  [{method}] sy={sy:.2f} → center {pos_y}%\n')
                else:
                    face_position = "center 15%"
                    sys.stderr.write(f'  [fallback] center 15%\n')
        except Exception as e:
            face_position = "center 15%"
            sys.stderr.write(f'  [error] {e}\n')

    print(json.dumps({
        'date': iso_date, 'artist': artist,
        'keywords': all_keywords, 'orientation': orientation,
        'width': w, 'height': h, 'facePosition': face_position,
    }))

except Exception as e:
    print(json.dumps({
        'date':None,'artist':None,'keywords':[],
        'orientation':'landscape','width':0,'height':0,'facePosition':None
    }))
    sys.stderr.write(str(e)+'\n')
