
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from werkzeug.utils import secure_filename

from functools import wraps
from datetime import datetime
import os
import uuid


# ============================================================
# CONFIGURATION
# ============================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = "niger-alert-secret-key"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///niger_alert.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# ============================================================
# CONFIGURATION DES UPLOADS
# ============================================================

UPLOAD_FOLDER = os.path.join(
    app.static_folder,
    "uploads"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

MAX_FILE_SIZE = 5 * 1024 * 1024

app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


# Créer automatiquement le dossier uploads
os.makedirs(
    app.config["UPLOAD_FOLDER"],
    exist_ok=True
)


def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# BASE DE DONNÉES
# ============================================================

db = SQLAlchemy(app)


# ============================================================
# FLASK LOGIN
# ============================================================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "user_login"

login_manager.login_message = (
    "Veuillez vous connecter pour accéder à cette page."
)


# ============================================================
# MODÈLE ADMINISTRATEUR
# ============================================================

class Admin(db.Model, UserMixin):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(30),
        default="admin",
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )


    def get_id(self):
        return f"admin:{self.id}"


# ============================================================
# MODÈLE UTILISATEUR / CITOYEN
# ============================================================

class User(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True, nullable=False)

    email = db.Column(db.String(150), unique=True, nullable=False)

    password = db.Column(db.String(255), nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def get_id(self):
        return f"user:{self.id}"







# ============================================================
# MODÈLE SIGNALEMENT
# ============================================================

class Report(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # ========================================================
    # UTILISATEUR AYANT ENVOYÉ LE SIGNALEMENT
    # ========================================================

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "reports",
            lazy=True
        )
    )

    # ========================================================
    # INFORMATIONS DU SIGNALEMENT
    # ========================================================

    incident_type = db.Column(
        db.String(100),
        nullable=False
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    region = db.Column(
        db.String(100),
        nullable=False
    )

    city = db.Column(
        db.String(100),
        nullable=False
    )

    address = db.Column(
        db.String(200)
    )

    urgency = db.Column(
        db.String(50),
        nullable=False
    )

    latitude = db.Column(
        db.String(50)
    )

    longitude = db.Column(
        db.String(50)
    )

    image = db.Column(
        db.String(200)
    )

    status = db.Column(
        db.String(50),
        default="en attente",
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

# ============================================================
# CHARGEMENT DE L'UTILISATEUR
# ============================================================

@login_manager.user_loader
def load_user(user_id):

    try:
        user_type, numeric_id = user_id.split(":", 1)
        numeric_id = int(numeric_id)
    except (AttributeError, ValueError):
        return None

    if user_type == "admin":
        return db.session.get(Admin, numeric_id)

    if user_type == "user":
        return db.session.get(User, numeric_id)

    return None





# ============================================================
# DÉCONNEXION AUTOMATIQUE DU CITOYEN APRÈS UN SIGNALEMENT
# ============================================================

@app.before_request
def check_report_logout():

    # Aucun délai programmé
    logout_at = session.get("logout_at")

    if not logout_at:
        return

    # Vérifier uniquement les utilisateurs citoyens
    if (
        current_user.is_authenticated
        and isinstance(current_user, User)
    ):

        if datetime.utcnow().timestamp() >= logout_at:

            logout_user()

            session.pop("logout_at", None)

            flash(
                "Votre session a expiré 5 minutes après votre signalement.",
                "info"
            )

            return redirect(url_for("user_login"))

# ============================================================
# PROTECTION ADMIN PRINCIPAL
# ============================================================

def admin_required(function):

    @wraps(function)
    @login_required
    def decorated_function(*args, **kwargs):

        if not isinstance(current_user, Admin):
            flash("Accès réservé aux administrateurs.", "danger")
            return redirect(url_for("index"))

        if not current_user.is_active:
            logout_user()
            flash("Votre compte administrateur est désactivé.", "danger")
            return redirect(url_for("admin_login"))

        return function(*args, **kwargs)

    return decorated_function


def principal_required(function):

    @wraps(function)
    @admin_required
    def decorated_function(*args, **kwargs):

        if current_user.role != "principal":
            flash("Accès réservé à l'administrateur principal.", "danger")
            return redirect(url_for("admin_dashboard"))

        return function(*args, **kwargs)

    return decorated_function


# ============================================================
# PAGE D'ACCUEIL
# ============================================================

@app.route("/")
def index():

    # Signalements en attente
    pending_reports = Report.query.filter_by(
        status="en attente"
    ).count()

    # Signalements traités
    processed_reports = Report.query.filter_by(
        status="traite"
    ).count()

    # Signalements en cours
    in_progress_reports = Report.query.filter_by(
        status="en cours"
    ).count()

    return render_template(
        "index.html",
        pending_reports=pending_reports,
        processed_reports=processed_reports,
        in_progress_reports=in_progress_reports
    )

# aboot ------------------------------------------------

@app.route("/about")
def about():
    return render_template("about.html")


# ============================================================
# PAGE CARTE
# ============================================================

@app.route("/map")
def map_page():

    reports = Report.query.filter(
        Report.latitude.isnot(None),
        Report.longitude.isnot(None)
    ).all()

    return render_template(
        "map.html",
        reports=reports
    )


# ============================================================
# PAGE SIGNALEMENT
# ============================================================

@app.route(
    "/report",
    methods=["GET", "POST"]
)
@login_required
def report():

    if request.method == "POST":

        incident_type = request.form.get(
            "incident_type",
            ""
        ).strip()

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        region = request.form.get(
            "region",
            ""
        ).strip()

        city = request.form.get(
            "city",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        urgency = request.form.get(
            "urgency",
            ""
        ).strip()

        latitude = request.form.get(
            "latitude",
            ""
        ).strip()

        longitude = request.form.get(
            "longitude",
            ""
        ).strip()


        # ====================================================
        # VALIDATION DES CHAMPS
        # ====================================================

        if not incident_type:
            flash(
                "Veuillez sélectionner le type d'incident.",
                "danger"
            )

            return redirect(
                url_for("report")
            )


        if not title:
            flash(
                "Veuillez saisir un titre.",
                "danger"
            )

            return redirect(
                url_for("report")
            )


        if not description:
            flash(
                "Veuillez décrire le problème.",
                "danger"
            )

            return redirect(
                url_for("report")
            )


        if not region:
            flash(
                "Veuillez sélectionner une région.",
                "danger"
            )

            return redirect(
                url_for("report")
            )


        if not city:
            flash(
                "Veuillez saisir une ville.",
                "danger"
            )

            return redirect(
                url_for("report")
            )


        if not urgency:
            flash(
                "Veuillez sélectionner le niveau d'urgence.",
                "danger"
            )

            return redirect(
                url_for("report")
            )


        # ====================================================
        # UPLOAD IMAGE
        # ====================================================

        image = request.files.get("image")

        image_filename = None


        if image and image.filename:

            if not allowed_file(
                image.filename
            ):

                flash(
                    "Format d'image non autorisé. Utilisez JPG, PNG ou WEBP.",
                    "danger"
                )

                return redirect(
                    url_for("report")
                )


            extension = image.filename.rsplit(
                ".",
                1
            )[1].lower()


            unique_name = (
                f"{uuid.uuid4()}.{extension}"
            )


            filename = secure_filename(
                unique_name
            )


            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )


            image.save(
                image_path
            )


            image_filename = filename


        # ====================================================
        # CRÉATION DU SIGNALEMENT
        # ====================================================
        new_report = Report(

    # Utilisateur connecté qui envoie le signalement
    user_id=current_user.id,

    incident_type=incident_type,

    title=title,

    description=description,

    region=region,

    city=city,

    address=address,

    urgency=urgency,

    latitude=latitude,

    longitude=longitude,

    image=image_filename,

    status="en attente"

)

        db.session.add(
            new_report
        )

        db.session.commit()
        # ============================================================
# DÉCONNEXION AUTOMATIQUE DU CITOYEN APRÈS UN SIGNALEMENT
# ============================================================

        session["logout_at"] = datetime.utcnow().timestamp() + 60


        flash(
            "Votre signalement a été envoyé avec succès.",
            "success"
        )


        return redirect(
            url_for("index")
        )


    return render_template(
        "report.html"
    )


# ============================================================
# LISTE DES SIGNALEMENTS PUBLICS
# ============================================================

@app.route("/alerts")
def alerts():

    reports = Report.query.order_by(
        Report.created_at.desc()
    ).all()

    return render_template(
        "alerts.html",
        reports=reports
    )


# ============================================================
# CONNEXION CITOYEN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def user_login():

    if current_user.is_authenticated:
        if isinstance(current_user, Admin):
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("index"))

    next_page = request.args.get("next") or request.form.get("next")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            if not user.is_active:
                flash("Votre compte est désactivé. Contactez l'administrateur.", "danger")
                return redirect(url_for("user_login"))

            login_user(user)
            flash(f"Bienvenue {user.username}.", "success")

            if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)

            return redirect(url_for("report"))

        flash("Nom d'utilisateur ou mot de passe incorrect.", "danger")

    return render_template("login.html", next_page=next_page)


# ============================================================
# INSCRIPTION CITOYEN
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def user_register():

    if current_user.is_authenticated:
        if isinstance(current_user, Admin):
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("index"))

    next_page = request.args.get("next") or request.form.get("next")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(username) < 3:
            flash("Le nom d'utilisateur doit contenir au moins 3 caractères.", "danger")
            return render_template("register.html", next_page=next_page)

        if not email or "@" not in email:
            flash("Veuillez saisir une adresse e-mail valide.", "danger")
            return render_template("register.html", next_page=next_page)

        if len(password) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", "danger")
            return render_template("register.html", next_page=next_page)

        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return render_template("register.html", next_page=next_page)

        if User.query.filter_by(username=username).first():
            flash("Ce nom d'utilisateur existe déjà.", "warning")
            return render_template("register.html", next_page=next_page)

        if User.query.filter_by(email=email).first():
            flash("Cette adresse e-mail est déjà utilisée.", "warning")
            return render_template("register.html", next_page=next_page)

        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            is_active=True
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Votre compte a été créé avec succès. Vous pouvez maintenant vous connecter.", "success")

        login_url = url_for("user_login")
        if next_page and next_page.startswith("/") and not next_page.startswith("//"):
            login_url = url_for("user_login", next=next_page)
        return redirect(login_url)

    return render_template("register.html", next_page=next_page)


# ============================================================
# DÉCONNEXION CITOYEN
# ============================================================

@app.route("/logout")
def user_logout():

    if current_user.is_authenticated and isinstance(current_user, Admin):
        return redirect(url_for("admin_logout"))

    logout_user()
    flash("Vous avez été déconnecté.", "success")
    return redirect(url_for("index"))


# ============================================================
# CONNEXION ADMIN
# ============================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if current_user.is_authenticated:

        if isinstance(current_user, Admin):
            return redirect(
                url_for("admin_dashboard")
            )

        logout_user()


    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        admin = Admin.query.filter_by(
            username=username
        ).first()


        if admin and check_password_hash(
            admin.password,
            password
        ):

            if not admin.is_active:

                flash(
                    "Votre compte administrateur est désactivé.",
                    "danger"
                )

                return redirect(
                    url_for("admin_login")
                )


            login_user(
                admin
            )


            flash(
                f"Bienvenue {admin.username}.",
                "success"
            )


            return redirect(
                url_for("admin_dashboard")
            )


        flash(
            "Nom d'utilisateur ou mot de passe incorrect.",
            "danger"
        )


    return render_template(
        "admin_login.html"
    )


# ============================================================
# INSCRIPTION ADMINISTRATEUR
# ============================================================
#
# IMPORTANT :
# Cette route permet uniquement de créer un compte admin.
# Pour la sécurité, les autres administrateurs doivent être
# créés depuis l'espace de l'administrateur principal.
#
# ============================================================

@app.route(
    "/admin/register",
    methods=["POST"]
)
def admin_register():

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )


    if not username:

        flash(
            "Veuillez saisir un nom d'utilisateur.",
            "danger"
        )

        return redirect(
            url_for("admin_login")
        )


    if len(username) < 3:

        flash(
            "Le nom d'utilisateur doit contenir au moins 3 caractères.",
            "danger"
        )

        return redirect(
            url_for("admin_login")
        )


    if len(password) < 6:

        flash(
            "Le mot de passe doit contenir au moins 6 caractères.",
            "danger"
        )

        return redirect(
            url_for("admin_login")
        )


    if password != confirm_password:

        flash(
            "Les mots de passe ne correspondent pas.",
            "danger"
        )

        return redirect(
            url_for("admin_login")
        )


    existing_admin = Admin.query.filter_by(
        username=username
    ).first()


    if existing_admin:

        flash(
            "Ce nom d'utilisateur existe déjà.",
            "warning"
        )

        return redirect(
            url_for("admin_login")
        )


    new_admin = Admin(

        username=username,

        password=generate_password_hash(
            password
        ),

        role="admin",

        is_active=True

    )


    db.session.add(
        new_admin
    )

    db.session.commit()


    flash(
        "Compte administrateur créé avec succès. Vous pouvez maintenant vous connecter.",
        "success"
    )


    return redirect(
        url_for("admin_login")
    )


# ============================================================
# DASHBOARD ADMIN
# ============================================================

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    reports = Report.query.order_by(
        Report.created_at.desc()
    ).all()


    total_reports = Report.query.count()


    pending_reports = Report.query.filter_by(
        status="en attente"
    ).count()


    processed_reports = Report.query.filter_by(
        status="traite"
    ).count()


    in_progress_reports = Report.query.filter_by(
        status="en cours"
    ).count()


    return render_template(
        "admin_dashboard.html",

        reports=reports,

        total_reports=total_reports,

        pending_reports=pending_reports,

        processed_reports=processed_reports,

        in_progress_reports=in_progress_reports
    )


# ============================================================
# LISTE DES ADMINISTRATEURS
# ============================================================

@app.route("/admin/administrators")
@principal_required
def administrators():

    admins = Admin.query.order_by(
        Admin.id.asc()
    ).all()


    return render_template(
        "admins.html",
        admins=admins
    )


# ============================================================
# AJOUTER UN ADMINISTRATEUR
# ============================================================

@app.route(
    "/admin/administrators/add",
    methods=["POST"]
)
@principal_required
def add_admin():

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )


    if len(username) < 3:

        flash(
            "Le nom d'utilisateur doit contenir au moins 3 caractères.",
            "danger"
        )

        return redirect(
            url_for("administrators")
        )


    if len(password) < 6:

        flash(
            "Le mot de passe doit contenir au moins 6 caractères.",
            "danger"
        )

        return redirect(
            url_for("administrators")
        )


    if password != confirm_password:

        flash(
            "Les mots de passe ne correspondent pas.",
            "danger"
        )

        return redirect(
            url_for("administrators")
        )


    existing_admin = Admin.query.filter_by(
        username=username
    ).first()


    if existing_admin:

        flash(
            "Ce nom d'utilisateur existe déjà.",
            "warning"
        )

        return redirect(
            url_for("administrators")
        )


    new_admin = Admin(

        username=username,

        password=generate_password_hash(
            password
        ),

        role="admin",

        is_active=True

    )


    db.session.add(
        new_admin
    )

    db.session.commit()


    flash(
        f"L'administrateur {username} a été créé avec succès.",
        "success"
    )


    return redirect(
        url_for("administrators")
    )


# ============================================================
# ACTIVER / DÉSACTIVER UN ADMIN
# ============================================================

@app.route(
    "/admin/administrators/<int:admin_id>/toggle",
    methods=["POST"]
)
@principal_required
def toggle_admin(admin_id):

    admin = db.get_or_404(
        Admin,
        admin_id
    )


    if admin.role == "principal":

        flash(
            "Le compte principal ne peut pas être désactivé.",
            "danger"
        )

        return redirect(
            url_for("administrators")
        )


    admin.is_active = not admin.is_active


    db.session.commit()


    if admin.is_active:

        message = (
            f"Le compte {admin.username} est maintenant actif."
        )

    else:

        message = (
            f"Le compte {admin.username} a été désactivé."
        )


    flash(
        message,
        "success"
    )


    return redirect(
        url_for("administrators")
    )


# ============================================================
# SUPPRIMER UN ADMIN
# ============================================================

@app.route(
    "/admin/administrators/<int:admin_id>/delete",
    methods=["POST"]
)
@principal_required
def delete_admin(admin_id):

    admin = db.get_or_404(
        Admin,
        admin_id
    )


    if admin.role == "principal":

        flash(
            "L'administrateur principal ne peut pas être supprimé.",
            "danger"
        )

        return redirect(
            url_for("administrators")
        )


    db.session.delete(
        admin
    )

    db.session.commit()


    flash(
        f"L'administrateur {admin.username} a été supprimé.",
        "success"
    )


    return redirect(
        url_for("administrators")
    )


# ============================================================
# DÉTAIL D'UN SIGNALEMENT
# ============================================================




@app.route(
    "/admin/report/<int:report_id>"
)
@admin_required
def admin_report_detail(report_id):

    report = db.get_or_404(
        Report,
        report_id
    )


    return render_template(
        "admin_report_detail.html",
        report=report
    )


# ============================================================
# MODIFICATION DU STATUT
# ============================================================

@app.route(
    "/admin/report/<int:report_id>/status",
    methods=["POST"]
)
@admin_required
def update_report_status(report_id):

    report = db.get_or_404(
        Report,
        report_id
    )


    new_status = request.form.get(
        "status"
    )


    allowed_statuses = [
        "en attente",
        "en cours",
        "traite"
    ]


    if new_status in allowed_statuses:

        report.status = new_status

        db.session.commit()


        flash(
            "Le statut du signalement a été mis à jour.",
            "success"
        )

    else:

        flash(
            "Statut invalide.",
            "danger"
        )


    return redirect(
        url_for(
            "admin_report_detail",
            report_id=report.id
        )
    )


# ============================================================
# SUPPRESSION D'UN SIGNALEMENT
# ============================================================

@app.route(
    "/admin/report/<int:report_id>/delete",
    methods=["POST"]
)
@admin_required
def delete_report(report_id):

    report = db.get_or_404(
        Report,
        report_id
    )


    # Supprimer également l'image associée
    if report.image:

        image_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            report.image
        )


        if os.path.exists(image_path):

            os.remove(
                image_path
            )


    db.session.delete(
        report
    )

    db.session.commit()


    flash(
        "Le signalement a été supprimé avec succès.",
        "success"
    )


    return redirect(
        url_for("admin_dashboard")
    )

# ============================================================
# STATISTIQUES ADMIN
# ============================================================

@app.route("/admin/statistics")
@admin_required
def admin_statistics():

    # ========================================================
    # TOTAL DES SIGNALEMENTS
    # ========================================================

    total_reports = Report.query.count()


    # ========================================================
    # SIGNALEMENTS PAR STATUT
    # ========================================================

    pending_reports = Report.query.filter_by(
        status="en attente"
    ).count()


    processing_reports = Report.query.filter_by(
        status="en cours"
    ).count()


    processed_reports = Report.query.filter_by(
        status="traite"
    ).count()


    # ========================================================
    # SIGNALEMENTS URGENTS
    # ========================================================

    urgent_reports = Report.query.filter_by(
        urgency="elevee"
    ).count()


    # ========================================================
    # TAUX DE TRAITEMENT
    # ========================================================

    if total_reports > 0:

        treatment_rate = round(
            (processed_reports / total_reports) * 100
        )

    else:

        treatment_rate = 0


    # ========================================================
    # STATISTIQUES PAR TYPE D'INCIDENT
    # ========================================================

    incident_results = db.session.query(
        Report.incident_type,
        func.count(Report.id)
    ).group_by(
        Report.incident_type
    ).all()


    incident_labels = [
        incident_type.capitalize()
        for incident_type, count in incident_results
    ]


    incident_values = [
        count
        for incident_type, count in incident_results
    ]


    # ========================================================
    # STATISTIQUES PAR STATUT
    # ========================================================

    status_results = db.session.query(
        Report.status,
        func.count(Report.id)
    ).group_by(
        Report.status
    ).all()


    status_labels = [
        status.capitalize()
        for status, count in status_results
    ]


    status_values = [
        count
        for status, count in status_results
    ]


    # ========================================================
    # STATISTIQUES PAR RÉGION
    # ========================================================

    region_statistics = db.session.query(
        Report.region,
        func.count(Report.id)
    ).group_by(
        Report.region
    ).order_by(
        func.count(Report.id).desc()
    ).all()


    # ========================================================
    # AFFICHAGE DE LA PAGE
    # ========================================================

    return render_template(
        "admin_statistics.html",

        total_reports=total_reports,

        pending_reports=pending_reports,

        processing_reports=processing_reports,

        processed_reports=processed_reports,

        urgent_reports=urgent_reports,

        treatment_rate=treatment_rate,

        incident_labels=incident_labels,

        incident_values=incident_values,

        status_labels=status_labels,

        status_values=status_values,

        region_statistics=region_statistics
    )

# ============================================================
# DÉCONNEXION ADMIN
# ============================================================

@app.route("/admin/logout")
@admin_required
def admin_logout():

    logout_user()


    flash(
        "Vous avez été déconnecté.",
        "success"
    )


    return redirect(
        url_for("admin_login")
    )




# ============================================================
# CRÉATION DU PREMIER ADMINISTRATEUR
# ============================================================

def create_default_admin():

    admin = Admin.query.filter_by(
        username="admin"
    ).first()


    if not admin:

        default_admin = Admin(

            username="admin",

            password=generate_password_hash(
                "admin123"
            ),

            role="principal",

            is_active=True

        )


        db.session.add(
            default_admin
        )


        db.session.commit()


        print(
            "=========================================="
        )

        print(
            "Administrateur principal créé avec succès."
        )

        print(
            "Nom d'utilisateur : admin"
        )

        print(
            "Mot de passe : admin123"
        )

        print(
            "Rôle : principal"
        )

        print(
            "=========================================="
        )


    else:

        # Si l'ancien compte admin existe déjà mais
        # possède le mauvais rôle, on le transforme
        # en administrateur principal.

        if admin.role != "principal":

            admin.role = "principal"

            admin.is_active = True

            db.session.commit()

            print(
                "Le compte admin existant a été configuré comme principal."
            )


# ============================================================
# GESTION DES ERREURS DE FICHIER TROP VOLUMINEUX
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    flash(
        "L'image est trop volumineuse. La taille maximale est de 5 Mo.",
        "danger"
    )

    return redirect(
        url_for("report")
    )





# ============================================================
# LANCEMENT DE L'APPLICATION
# ============================================================

if __name__ == "__main__":

    with app.app_context():

        # Création des tables
        db.create_all()

        # Création / configuration du premier admin
        create_default_admin()

app.run(host='0.0.0.0', port=5000, debug=True)

