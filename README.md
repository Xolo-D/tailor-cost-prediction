# Tailor Cost Prediction System
### University of Zululand – Group 7
### Django + Scikit-learn Cost Estimation App

---

## Project Structure

```
tailor_project/
│
├── manage.py
├── requirements.txt
├── db.sqlite3                        ← created after migrations
│
├── tailor_project/                   ← Django project config
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
└── estimator/                        ← main Django app
    ├── __init__.py
    ├── apps.py                       ← loads ML model at startup
    ├── admin.py                      ← Django admin registration
    ├── forms.py                      ← Login, Register, Profile, Estimate forms
    ├── models.py                     ← TailorProfile, EstimateHistory
    ├── views.py                      ← All views (auth, estimator, history, profile)
    ├── urls.py                       ← App URL routes
    │
    ├── ml/
    │   ├── __init__.py
    │   ├── predictor.py              ← ML model wrapper (load + predict)
    │   ├── fine_tuned_random_forest_regressor.joblib   ← YOUR MODEL
    │   └── group_7_dataset.csv       ← YOUR DATASET
    │
    ├── static/
    │   ├── css/
    │   │   ├── style.css             ← Main styles (from your design)
    │   │   └── auth.css              ← Login/register styles
    │   └── js/
    │       └── estimator.js          ← AJAX + chat JS
    │
    ├── templates/estimator/
    │   ├── base.html
    │   ├── login.html                ← Login page
    │   ├── register.html             ← Sign up page
    │   ├── estimator.html            ← Main estimator UI
    │   ├── history.html              ← Estimate history table
    │   └── profile.html              ← User profile
    │
    └── management/commands/
        └── create_admin.py           ← Quick admin creation command
```

---

## Quick Setup (Step-by-Step)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run database migrations
```bash
python manage.py makemigrations estimator
python manage.py migrate
```

### 3. Create admin user
```bash
# Default: admin@unizulu.ac.za / admin1234
python manage.py create_admin

# Or custom:
python manage.py create_admin --email yourname@unizulu.ac.za --password yourpass
```

### 4. Start the server
```bash
python manage.py runserver
```

### 5. Open in browser
- **App:** http://127.0.0.1:8000/login/
- **Admin:** http://127.0.0.1:8000/admin/

---

## URL Routes

| URL               | View            | Description                        |
|-------------------|-----------------|------------------------------------|
| `/login/`         | login_view      | Login page (email + password)      |
| `/register/`      | register_view   | Sign up / create account           |
| `/logout/`        | logout_view     | Signs out and redirects to login   |
| `/estimator/`     | estimator_view  | Main cost estimator (form + result)|
| `/api/predict/`   | predict_ajax    | AJAX prediction endpoint (JSON)    |
| `/api/chat/`      | chat_predict    | Natural language chat endpoint     |
| `/history/`       | history_view    | Paginated estimate history         |
| `/history/delete/<id>/` | delete_estimate | Delete one estimate          |
| `/profile/`       | profile_view    | View and edit tailor profile       |
| `/admin/`         | Django Admin    | Manage users, profiles, estimates  |

---

## Model Inputs & Outputs

### Inputs (from the form)
| Field        | Type   | Example    |
|--------------|--------|------------|
| Garment      | Select | Dress      |
| Fabric_Type  | Select | Silk       |
| Fabric_m     | Float  | 2.5        |

### Outputs (displayed in result panels)
| Field            | Description                          |
|------------------|--------------------------------------|
| Material_Cost_ZAR| Fabric_m × Price_per_m               |
| Labour_Cost      | Derived from Total − Material − 8%   |
| Overhead_Cost    | 8% of Total Cost                     |
| Total_Cost_ZAR   | Predicted by Random Forest model     |

### Price per Metre Reference
| Fabric    | Avg Price/m (ZAR) |
|-----------|-------------------|
| Cotton    | R 90              |
| Denim     | R 114             |
| Leather   | R 275             |
| Linen     | R 140             |
| Nylon     | R 70              |
| Polyester | R 68              |
| Silk      | R 173             |
| Wool      | R 217             |

---

## ML Model Notes

The system uses a **Random Forest Regressor** wrapped in a sklearn Pipeline with:
- `OneHotEncoder` for Garment and Fabric_Type
- Numeric passthrough for Fabric_m and Price_per_m

**Version mismatch handling:** If the saved `.joblib` file was trained on a different
sklearn version, the system automatically retrains a new Random Forest from
`group_7_dataset.csv` at startup. The retrained model is saved as
`fine_tuned_random_forest_regressor_retrained.joblib` for future use.

---

## Features

- ✅ Login / Sign Up / Sign Out (email-based auth)
- ✅ Tailor profile with avatar initials and stats
- ✅ Cost + Material estimation with breakdown
- ✅ Nearest comparable garments from dataset
- ✅ Estimate history with filters + pagination
- ✅ Delete estimates from history
- ✅ Natural language chat input ("silk dress 3m")
- ✅ AJAX prediction (no page reload)
- ✅ Django Admin dashboard
- ✅ Responsive layout (mobile sidebar collapses)

---

## Django Admin

Access at `/admin/` with your superuser credentials.

**Registered models:**
- **TailorProfile** – view all tailor accounts
- **EstimateHistory** – view/filter/search all estimates across all users

---

## Deployment Notes (Production)

1. Set `DEBUG = False` in `settings.py`
2. Change `SECRET_KEY` to a secure random string
3. Set `ALLOWED_HOSTS = ['yourdomain.com']`
4. Run `python manage.py collectstatic`
5. Use gunicorn + nginx in production
6. Use PostgreSQL instead of SQLite for production

---

## Troubleshooting

**"No module named 'sklearn'"**
→ Run `pip install scikit-learn`

**Model version warning**
→ The system will auto-retrain. Check logs for "Model retrained."

**Migrations error**
→ Delete `db.sqlite3` and re-run `python manage.py migrate`

**Static files not loading**
→ Run `python manage.py collectstatic` or confirm `STATICFILES_DIRS` path is correct
