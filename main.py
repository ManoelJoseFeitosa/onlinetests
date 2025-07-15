# ===================================================================
# SEÇÃO 1: IMPORTS
# ===================================================================
import os
from dotenv import load_dotenv
load_dotenv()
import resend
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
import random
from weasyprint import HTML, CSS
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, UniqueConstraint, func, and_
import json

# ===================================================================
# SEÇÃO 2: CONFIGURAÇÃO DO APLICATIVO E EXTENSÕES
# ===================================================================
app = Flask(__name__,
            template_folder='site/templates',
            static_folder='site/static')

UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads/questoes')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SECRET_KEY'] = 'uma_chave_secreta_muito_forte_e_dificil_de_adivinhar'

# --- FORMA ROBUSTA DE CARREGAR A URL DO BANCO ---
load_dotenv() 
database_uri = os.getenv('DATABASE_URL')
if not database_uri:
    raise ValueError("A variável de ambiente DATABASE_URL não foi encontrada. Verifique seu arquivo .env.")

if database_uri.startswith("postgres://"):
    database_uri = database_uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = "info"

# ===================================================================
# SEÇÃO 3: DECORATOR DE AUTORIZAÇÃO
# ===================================================================
def role_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                if request.accept_mimetypes.best_match(['application/json']):
                    return jsonify({'error': 'Acesso não autorizado para este perfil.'}), 403
                flash("Você não tem permissão para acessar esta página.", "danger")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_superadmin:
            flash("Você não tem permissão para acessar esta área.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ===================================================================
# SEÇÃO 4: MODELOS DO BANCO DE DADOS
# ===================================================================
# (Seu código de modelos está correto e permanece o mesmo)
simulado_disciplinas = db.Table('simulado_disciplinas',
    db.Column('avaliacao_id', db.Integer, db.ForeignKey('avaliacao.id'), primary_key=True),
    db.Column('disciplina_id', db.Integer, db.ForeignKey('disciplina.id'), primary_key=True)
)
avaliacao_questoes = db.Table('avaliacao_questoes',
    db.Column('avaliacao_id', db.Integer, db.ForeignKey('avaliacao.id'), primary_key=True),
    db.Column('questao_id', db.Integer, db.ForeignKey('questao.id'), primary_key=True)
)
professor_disciplinas = db.Table('professor_disciplinas',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuario.id'), primary_key=True),
    db.Column('disciplina_id', db.Integer, db.ForeignKey('disciplina.id'), primary_key=True)
)
serie_disciplinas = db.Table('serie_disciplinas',
    db.Column('serie_id', db.Integer, db.ForeignKey('serie.id'), primary_key=True),
    db.Column('disciplina_id', db.Integer, db.ForeignKey('disciplina.id'), primary_key=True)
)
professor_series = db.Table('professor_series',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuario.id'), primary_key=True),
    db.Column('serie_id', db.Integer, db.ForeignKey('serie.id'), primary_key=True)
)
avaliacao_alunos_designados = db.Table('avaliacao_alunos_designados',
    db.Column('avaliacao_id', db.Integer, db.ForeignKey('avaliacao.id'), primary_key=True),
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuario.id'), primary_key=True)
)

class AnoLetivo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ano = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='ativo', nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escola.id'), nullable=False)
    escola = db.relationship('Escola', backref='anos_letivos')
    __table_args__ = (UniqueConstraint('ano', 'escola_id', name='_ano_escola_uc'),)

class Matricula(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    serie_id = db.Column(db.Integer, db.ForeignKey('serie.id'), nullable=False)
    ano_letivo_id = db.Column(db.Integer, db.ForeignKey('ano_letivo.id'), nullable=False)
    status = db.Column(db.String(30), default='cursando', nullable=False)
    aluno = db.relationship('Usuario', backref=db.backref('matriculas', cascade="all, delete-orphan"))
    serie = db.relationship('Serie')
    ano_letivo = db.relationship('AnoLetivo', backref='matriculas')

class Escola(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), unique=True, nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='ativo', nullable=False)

class Serie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escola.id'), nullable=False)
    disciplinas = db.relationship('Disciplina', secondary=serie_disciplinas, lazy='subquery',
                                  backref=db.backref('series', lazy=True))
    escola = db.relationship('Escola', backref='series')
    __table_args__ = (UniqueConstraint('nome', 'escola_id', name='_nome_escola_uc_serie'),)

class Disciplina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escola.id'), nullable=False)
    questoes = db.relationship('Questao', backref='disciplina', lazy=True, cascade="all, delete")
    escola = db.relationship('Escola', backref='disciplinas')
    __table_args__ = (UniqueConstraint('nome', 'escola_id', name='_nome_escola_uc_disciplina'),)
    def to_dict(self):
        return {'id': self.id, 'nome': self.nome}

class Questao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplina.id'), nullable=False)
    serie_id = db.Column(db.Integer, db.ForeignKey('serie.id'), nullable=False)
    criador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    assunto = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False, default='multipla_escolha')
    texto = db.Column(db.Text, nullable=False)
    imagem_nome = db.Column(db.String(255), nullable=True)
    imagem_alt = db.Column(db.String(500), nullable=True, comment="Texto alternativo para acessibilidade")
    nivel = db.Column(db.String(10), nullable=False, server_default='media', comment="Nível de dificuldade (facil, media, dificil)")
    opcao_a = db.Column(db.Text)
    opcao_b = db.Column(db.Text)
    opcao_c = db.Column(db.Text)
    opcao_d = db.Column(db.Text)
    gabarito = db.Column(db.String(1))
    justificativa_gabarito = db.Column(db.Text, nullable=True)
    serie = db.relationship('Serie')
    criador = db.relationship('Usuario', backref='questoes_criadas')

class Avaliacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, server_default='prova')
    tempo_limite = db.Column(db.Integer, nullable=True)
    criador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplina.id'), nullable=True)
    serie_id = db.Column(db.Integer, db.ForeignKey('serie.id'), nullable=True)
    escola_id = db.Column(db.Integer, db.ForeignKey('escola.id'), nullable=False)
    ano_letivo_id = db.Column(db.Integer, db.ForeignKey('ano_letivo.id'), nullable=True)
    is_dinamica = db.Column(db.Boolean, default=False, nullable=False)
    modelo_id = db.Column(db.Integer, db.ForeignKey('modelo_avaliacao.id'), nullable=True)
    alunos_designados = db.relationship('Usuario', secondary=avaliacao_alunos_designados, lazy='subquery',
                                        backref=db.backref('avaliacoes_designadas', lazy=True))
    ano_letivo = db.relationship('AnoLetivo', backref='avaliacoes')
    modelo = db.relationship('ModeloAvaliacao', backref='avaliacoes_geradas')
    disciplinas_simulado = db.relationship('Disciplina', secondary=simulado_disciplinas, lazy='subquery',
                                           backref=db.backref('simulados', lazy=True))
    questoes = db.relationship('Questao', secondary=avaliacao_questoes, lazy='subquery',
                                     backref=db.backref('avaliacoes', lazy=True))
    resultados = db.relationship('Resultado', backref='avaliacao', lazy=True, cascade="all, delete")
    serie = db.relationship('Serie')
    disciplina = db.relationship('Disciplina', backref=db.backref('avaliacoes', lazy=True))
    escola = db.relationship('Escola', backref='avaliacoes')

class ModeloAvaliacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    tempo_limite = db.Column(db.Integer, nullable=True)
    criador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    serie_id = db.Column(db.Integer, db.ForeignKey('serie.id'), nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escola.id'), nullable=False)
    regras_selecao = db.Column(db.JSON, nullable=False)
    criador = db.relationship('Usuario')
    serie = db.relationship('Serie')
    escola = db.relationship('Escola')

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='aluno')
    precisa_trocar_senha = db.Column(db.Boolean, default=True, nullable=False)
    escola_id = db.Column(db.Integer, db.ForeignKey('escola.id'), nullable=True)
    is_superadmin = db.Column(db.Boolean, default=False, nullable=False)
    avaliacoes_criadas = db.relationship('Avaliacao', backref='criador', lazy=True, foreign_keys=[Avaliacao.criador_id])
    resultados = db.relationship('Resultado', backref='aluno', lazy=True, foreign_keys='Resultado.aluno_id', cascade="all, delete-orphan")
    disciplinas_lecionadas = db.relationship('Disciplina', secondary=professor_disciplinas, lazy='subquery',
                                             backref=db.backref('professores', lazy=True))
    series_lecionadas = db.relationship('Serie', secondary=professor_series, lazy='subquery',
                                        backref=db.backref('professores', lazy=True))
    escola = db.relationship('Escola', backref='usuarios')
    @property
    def serie_atual(self):
        if self.role == 'aluno':
            ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=self.escola_id, status='ativo').first()
            if ano_letivo_ativo:
                matricula_ativa = Matricula.query.filter_by(aluno_id=self.id, ano_letivo_id=ano_letivo_ativo.id).first()
                if matricula_ativa:
                    return matricula_ativa.serie
        return None

class Resultado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nota = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(50), default='Pendente')
    data_realizacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    avaliacao_id = db.Column(db.Integer, db.ForeignKey('avaliacao.id'), nullable=False)
    ano_letivo_id = db.Column(db.Integer, db.ForeignKey('ano_letivo.id'), nullable=True)
    ano_letivo = db.relationship('AnoLetivo', backref='resultados')
    respostas = db.relationship('Resposta', backref='resultado', lazy='dynamic', cascade="all, delete")

class Resposta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resultado_id = db.Column(db.Integer, db.ForeignKey('resultado.id'), nullable=False)
    questao_id = db.Column(db.Integer, db.ForeignKey('questao.id'), nullable=False)
    resposta_aluno = db.Column(db.Text)
    status_correcao = db.Column(db.String(20), default='nao_avaliada')
    pontos = db.Column(db.Float, default=0.0)
    feedback_professor = db.Column(db.Text)
    questao = db.relationship('Questao')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Fazer Login')

class TrocarSenhaForm(FlaskForm):
    password = PasswordField('Nova Senha', validators=[DataRequired()])
    confirm_password = PasswordField('Confirme a Nova Senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    submit = SubmitField('Atualizar Senha')

class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    user_email = db.Column(db.String(150), nullable=False)
    action = db.Column(db.String(100), nullable=False, index=True) # Ex: 'LOGIN_SUCCESS', 'QUESTION_CREATE'
    target_type = db.Column(db.String(50), nullable=True, index=True) # Ex: 'Usuario', 'Questao'
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.JSON, nullable=True) # Para armazenar dados extras, como 'antes' e 'depois'
    ip_address = db.Column(db.String(45), nullable=True)

    user = db.relationship('Usuario', backref='audit_logs')

    def __repr__(self):
        return f'<AuditLog {self.timestamp} - {self.user_email} - {self.action}>'

# ===================================================================
# SEÇÃO 5: ROTAS DA APLICAÇÃO
# ===================================================================
def log_audit(action, target_obj=None, details=None):
    """
    Registra um evento de auditoria.
    - action: Uma string descrevendo a ação (ex: 'USER_UPDATE').
    - target_obj: O objeto do banco de dados que foi modificado (opcional).
    - details: Um dicionário com informações extras (opcional).
    """
    try:
        # Cria a entrada do log sem o usuário primeiro
        log_entry = AuditLog(
            action=action,
            details=details,
            ip_address=request.remote_addr if request else None
        )

        # Tenta associar o usuário logado, se houver
        if current_user and current_user.is_authenticated:
            log_entry.user_id = current_user.id
            log_entry.user_email = current_user.email
        # Se não houver usuário logado (ex: falha de login), tenta pegar do formulário
        elif request and request.form:
            log_entry.user_email = request.form.get('email', 'N/A')
        else:
            log_entry.user_email = 'Sistema' # Para ações automáticas

        # Se um objeto alvo foi passado, registra seu tipo e ID
        if target_obj and hasattr(target_obj, 'id'):
            log_entry.target_type = target_obj.__class__.__name__
            log_entry.target_id = target_obj.id

        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        # Se houver um erro ao salvar o log, faz rollback para não quebrar a aplicação principal
        db.session.rollback()
        # Imprime o erro nos logs do servidor para depuração
        print(f"ERRO CRÍTICO AO SALVAR LOG DE AUDITORIA: {e}")

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized_callback():
    if request.accept_mimetypes.best_match(['application/json']):
        return jsonify({'error': 'Login necessário para acessar este recurso.'}), 401
    return redirect(url_for('login'))

@app.before_request
def before_request_handler():
    if current_user.is_authenticated and current_user.precisa_trocar_senha:
        public_endpoints = ['login', 'logout', 'static', 'pagina_inicial_vendas', 'funcionalidades', 'planos', 'contato', 'setup_inicial']
        if request.endpoint and request.endpoint not in public_endpoints and request.endpoint != 'trocar_senha':
            return redirect(url_for('trocar_senha'))

# --- Rotas Públicas e de SuperAdmin ---
@app.route('/setup-inicial')
def setup_inicial():
    if Usuario.query.filter_by(is_superadmin=True).count() == 0:
        super_admin = Usuario(nome="Super Admin", email="manoelbd2012@gmail.com", password=generate_password_hash("Mf@871277", method='pbkdf2:sha256'), role="coordenador", escola_id=None, is_superadmin=True, precisa_trocar_senha=False)
        db.session.add(super_admin)
        db.session.commit()
        return "Super Admin criado com sucesso!"
    return "Super Admin já existe."

@app.route('/')
def pagina_inicial_vendas():
    return render_template('home_vendas.html')

@app.route('/funcionalidades')
def funcionalidades():
    return render_template('funcionalidades.html')

@app.route('/planos')
def planos():
    return render_template('planos.html')

@app.route('/contato', methods=['GET', 'POST'])
def contato():
    # --- PONTO DE VERIFICAÇÃO 1 ---
    # Este print aparecerá nos logs toda vez que a página /contato for acessada.
    print("--- Rota /contato foi acessada ---")
    
    if request.method == 'POST':
        # --- PONTO DE VERIFICAÇÃO 2 ---
        # Este print só aparecerá se o formulário for enviado com o método POST.
        print("--- Método POST detectado. Tentando processar o formulário. ---")

        nome = request.form.get('nome')
        email_remetente = request.form.get('email')
        mensagem = request.form.get('mensagem')
        
        # --- PONTO DE VERIFICAÇÃO 3 ---
        # Vamos ver os dados que chegaram.
        print(f"Dados recebidos: Nome='{nome}', Email='{email_remetente}', Mensagem='{mensagem}'")

        if not nome or not email_remetente or not mensagem:
            flash('Por favor, preencha todos os campos obrigatórios.', 'danger')
            return render_template('contato.html')

        resend_api_key = os.environ.get('RESEND_API_KEY')

        # --- PONTO DE VERIFICAÇÃO 4 ---
        # Vamos verificar se a chave da API foi encontrada.
        if not resend_api_key:
            print("--- ERRO CRÍTICO: Chave da API do Resend (RESEND_API_KEY) não encontrada nas variáveis de ambiente! ---")
            flash('Ocorreu um erro de configuração no servidor. Por favor, tente novamente mais tarde.', 'danger')
            return render_template('contato.html')
        else:
            print("--- Chave da API do Resend encontrada com sucesso. ---")

        try:
            # --- PONTO DE VERIFICAÇÃO 5 ---
            # O código está prestes a tentar enviar o e-mail.
            print("--- Tentando enviar o e-mail com Resend... ---")
            
            resend.api_key = resend_api_key
            params = {
                "from": "Online Tests <onboarding@resend.dev>",
                "to": ["manoelbd2012@gmail.com"],
                "subject": f"Nova Mensagem de Contato de {nome}",
                "html": f"""
                    <h3>Nova Mensagem Recebida do Site</h3>
                    <p><strong>Nome:</strong> {nome}</p>
                    <p><strong>Email para contato:</strong> {email_remetente}</p>
                    <p><strong>Instituição:</strong> {request.form.get('escola') or 'Não informada'}</p>
                    <hr>
                    <p><strong>Mensagem:</strong></p>
                    <p>{mensagem.replace(os.linesep, '<br>')}</p>
                """,
                "reply_to": email_remetente
            }
            email_enviado = resend.Emails.send(params)
            
            # --- PONTO DE VERIFICAÇÃO 6 ---
            # Se você vir este print, o Resend aceitou o pedido.
            print(f"--- E-mail enviado para Resend. Resposta da API: {email_enviado} ---")
            
            flash('Sua mensagem foi enviada com sucesso! Entraremos em contato em breve.', 'success')
            return redirect(url_for('contato'))

        except Exception as e:
            # --- PONTO DE VERIFICAÇÃO 7 (ERRO) ---
            # Se algo der errado com a API do Resend, este print aparecerá.
            print(f"--- ERRO AO ENVIAR EMAIL COM RESEND: {e} ---")
            flash('Ocorreu um erro inesperado ao enviar sua mensagem. Por favor, tente novamente.', 'danger')
            return render_template('contato.html')
        
    return render_template('contato.html')

@app.route('/superadmin/painel')
@login_required
@superadmin_required
def superadmin_painel():
    escolas_com_contagem = db.session.query(Escola, func.count(Usuario.id)).outerjoin(Usuario, and_(Escola.id == Usuario.escola_id, Usuario.role == 'aluno')).group_by(Escola.id).order_by(Escola.nome).all()
    return render_template('app/superadmin_painel.html', escolas_com_contagem=escolas_com_contagem)

@app.route('/superadmin/escola/<int:escola_id>/toggle-status', methods=['POST'])
@login_required
@superadmin_required
def toggle_escola_status(escola_id):
    escola = Escola.query.get_or_404(escola_id)
    escola.status = 'bloqueado' if escola.status == 'ativo' else 'ativo'
    db.session.commit()
    flash(f"Status da escola {escola.nome} alterado.", "info")
    return redirect(url_for('superadmin_painel'))

@app.route('/superadmin/nova-escola', methods=['GET', 'POST'])
@login_required
@superadmin_required
def superadmin_nova_escola():
    if request.method == 'POST':
        nome_escola = request.form.get('nome_escola')
        cnpj_escola = request.form.get('cnpj_escola')
        nome_coordenador = request.form.get('nome_coordenador')
        email_coordenador = request.form.get('email_coordenador')
        senha_coordenador = request.form.get('senha_coordenador')
        if not all([nome_escola, nome_coordenador, email_coordenador, senha_coordenador]):
            flash("Todos os campos são obrigatórios.", "danger")
            return redirect(url_for('superadmin_nova_escola'))
        if Escola.query.filter_by(nome=nome_escola).first() or (cnpj_escola and Escola.query.filter_by(cnpj=cnpj_escola).first()):
            flash('Uma escola com este nome ou CNPJ já existe.', 'danger')
            return redirect(url_for('superadmin_nova_escola'))
        if Usuario.query.filter_by(email=email_coordenador).first():
            flash('Este e-mail já está sendo utilizado por outro usuário.', 'danger')
            return redirect(url_for('superadmin_nova_escola'))
        nova_escola = Escola(nome=nome_escola, cnpj=cnpj_escola)
        db.session.add(nova_escola)
        db.session.flush()
        ano_atual = datetime.now().year
        novo_ano_letivo = AnoLetivo(ano=ano_atual, escola_id=nova_escola.id, status='ativo')
        db.session.add(novo_ano_letivo)
        novo_coordenador = Usuario(nome=nome_coordenador, email=email_coordenador, password=generate_password_hash(senha_coordenador, method='pbkdf2:sha256'), role='coordenador', escola_id=nova_escola.id, precisa_trocar_senha=True)
        db.session.add(novo_coordenador)
        db.session.commit()
        flash(f'Escola "{nome_escola}" e seu coordenador foram criados com sucesso!', 'success')
        return redirect(url_for('superadmin_painel'))
    return render_template('app/nova_escola.html')

@app.route('/superadmin/editar-escola/<int:escola_id>', methods=['GET', 'POST'])
@login_required
@superadmin_required
def editar_escola(escola_id):
    escola = Escola.query.get_or_404(escola_id)
    coordenador = Usuario.query.filter_by(escola_id=escola.id, role='coordenador').first()
    if not coordenador:
        flash('Coordenador não encontrado para esta escola. Por favor, verifique os dados.', 'danger')
        return redirect(url_for('superadmin_painel'))
    if request.method == 'POST':
        escola.nome = request.form.get('nome_escola')
        escola.cnpj = request.form.get('cnpj_escola')
        coordenador.nome = request.form.get('nome_coordenador')
        coordenador.email = request.form.get('email_coordenador')
        nova_senha = request.form.get('senha_coordenador')
        if nova_senha:
            coordenador.password = generate_password_hash(nova_senha, method='pbkdf2:sha256')
            coordenador.precisa_trocar_senha = True
            flash('Senha do coordenador redefinida com sucesso!', 'info')
        try:
            db.session.commit()
            flash(f'Dados da escola "{escola.nome}" atualizados com sucesso!', 'success')
            return redirect(url_for('superadmin_painel'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar os dados: {e}', 'danger')
    return render_template('app/editar_escola.html', escola=escola, coordenador=coordenador)

# --- Rotas de Autenticação e Dashboard ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Se o usuário já estiver autenticado, redireciona para o dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter(func.lower(Usuario.email) == func.lower(form.email.data)).first()

        # 1. Verifica se o usuário existe e se a senha está correta
        if user and check_password_hash(user.password, form.password.data):
            
            # 2. Verifica se a escola do usuário está bloqueada (APENAS se for um usuário comum)
            if not user.is_superadmin and user.escola and user.escola.status == 'bloqueado':
                # AUDITORIA: Registra a tentativa de login em uma escola bloqueada
                log_audit('LOGIN_BLOCKED_SCHOOL', target_obj=user, details={'escola_nome': user.escola.nome})
                flash('O acesso para esta escola está temporariamente bloqueado.', 'danger')
                return redirect(url_for('login'))
            
            # Se tudo estiver correto, faz o login
            login_user(user)
            
            # AUDITORIA: Registra o login bem-sucedido
            log_audit('LOGIN_SUCCESS', target_obj=user)
            
            # Redireciona para a troca de senha se necessário
            if user.precisa_trocar_senha:
                flash('Este é o seu primeiro acesso. Por favor, crie uma nova senha.', 'info')
                return redirect(url_for('trocar_senha'))
            
            # Redireciona para o dashboard principal
            return redirect(url_for('dashboard'))
        
        else:
            # AUDITORIA: Registra a tentativa de login inválida (usuário não encontrado ou senha incorreta)
            # A função log_audit pegará o email do formulário automaticamente.
            log_audit('LOGIN_FAILURE')
            flash('Login inválido. Verifique seu e-mail e senha.', 'danger')
    
    return render_template('app/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Se for superadmin, redireciona para o painel dele
    if current_user.is_superadmin:
        return redirect(url_for('superadmin_painel'))

    # Para outros usuários (como o Coordenador), vamos verificar
    # se já existe um ano letivo ativo para a escola dele.
    ano_letivo_ativo = None
    if current_user.escola_id:
        ano_letivo_ativo = AnoLetivo.query.filter_by(
            escola_id=current_user.escola_id,
            status='ativo'
        ).first()

    # Agora passamos essa informação para o template.
    # Se 'ano_letivo_ativo' for None, significa que não há um ciclo ativo.
    return render_template('app/dashboard.html', ano_letivo_ativo=ano_letivo_ativo)

@app.route('/trocar-senha', methods=['GET', 'POST'])
@login_required
def trocar_senha():
    form = TrocarSenhaForm()
    if form.validate_on_submit():
        current_user.password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        current_user.precisa_trocar_senha = False
        db.session.commit()
        flash('Sua senha foi atualizada com sucesso!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('app/trocar_senha.html', form=form)

# --- Rotas de Administração do Coordenador ---
@app.route('/admin/gerenciar-ciclo', methods=['GET', 'POST'])
@login_required
@role_required('coordenador')
def gerenciar_ciclo():
    escola_id = current_user.escola_id
    anos_letivos = AnoLetivo.query.filter_by(escola_id=escola_id).order_by(AnoLetivo.ano.desc()).all()
    if request.method == 'POST':
        ano_novo = request.form.get('ano_novo', type=int)
        if ano_novo:
            existente = AnoLetivo.query.filter_by(ano=ano_novo, escola_id=escola_id).first()
            if existente:
                flash(f'O ano letivo {ano_novo} já existe.', 'danger')
            else:
                AnoLetivo.query.filter_by(escola_id=escola_id).update({'status': 'arquivado'})
                novo_ano = AnoLetivo(ano=ano_novo, escola_id=escola_id, status='ativo')
                db.session.add(novo_ano)
                db.session.commit()
                flash(f'Ano letivo {ano_novo} criado e definido como ativo!', 'success')
                return redirect(url_for('gerenciar_ciclo'))
    ano_atual = datetime.now().year
    return render_template('app/gerenciar_ciclo.html', anos_letivos=anos_letivos, ano_atual=ano_atual)

@app.route('/admin/gerenciar_usuarios', methods=['GET', 'POST'])
@login_required
@role_required('coordenador')
def gerenciar_usuarios():
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
    if not ano_letivo_ativo:
        flash('Nenhum ano letivo ativo encontrado. Por favor, crie um na página "Gerenciar Ciclo".', 'warning')
        return redirect(url_for('gerenciar_ciclo'))

    if request.method == 'POST':
        # --- Lógica de Pesquisa de Usuário ---
        if 'submit_pesquisa' in request.form:
            email_pesquisa = request.form.get('email_pesquisa')
            if not email_pesquisa:
                 flash('Por favor, digite um e-mail para pesquisar.', 'warning')
                 return redirect(url_for('gerenciar_usuarios'))

            # Melhoria: Busca case-insensitive para o e-mail
            usuario = Usuario.query.filter(
                func.lower(Usuario.email) == func.lower(email_pesquisa),
                Usuario.escola_id == current_user.escola_id
            ).first()

            if usuario:
                # AUDITORIA: Registra a busca por um usuário específico (opcional, mas bom para rastreabilidade)
                log_audit('USER_SEARCH_SUCCESS', details={'searched_email': email_pesquisa, 'found_user_id': usuario.id})
                return redirect(url_for('editar_usuario', user_id=usuario.id))
            else:
                # AUDITORIA: Registra que uma busca foi feita mas não encontrou resultados
                log_audit('USER_SEARCH_NOT_FOUND', details={'searched_email': email_pesquisa})
                flash('Nenhum usuário encontrado com este e-mail nesta escola.', 'danger')

        # --- Lógica de Cadastro de Novo Usuário ---
        elif 'submit_cadastro' in request.form:
            nome = request.form.get('nome')
            email = request.form.get('email')
            senha = request.form.get('senha')
            role = request.form.get('role')

            if not all([nome, email, senha, role]):
                flash('Todos os campos obrigatórios devem ser preenchidos.', 'warning')
                return redirect(url_for('gerenciar_usuarios'))

            # Melhoria: Verifica se o e-mail já existe de forma case-insensitive
            if Usuario.query.filter(func.lower(Usuario.email) == func.lower(email)).first():
                flash('Este e-mail já está cadastrado no sistema.', 'warning')
            else:
                try:
                    novo_usuario = Usuario(
                        nome=nome,
                        email=email,
                        password=generate_password_hash(senha, method='pbkdf2:sha256'),
                        role=role,
                        escola_id=current_user.escola_id
                    )
                    db.session.add(novo_usuario)

                    if role == 'aluno':
                        serie_id = request.form.get('serie_id', type=int)
                        if not serie_id:
                            flash('A série é obrigatória para cadastrar um aluno.', 'danger')
                            # O rollback acontece no bloco except
                            raise ValueError("Série não fornecida para o aluno.")
                        
                        # O flush atribui um ID ao novo_usuario antes do commit final
                        db.session.flush()
                        nova_matricula = Matricula(aluno_id=novo_usuario.id, serie_id=serie_id, ano_letivo_id=ano_letivo_ativo.id)
                        db.session.add(nova_matricula)

                    elif role == 'professor':
                        disciplinas_ids = request.form.getlist('disciplinas_ids')
                        series_ids = request.form.getlist('series_ids')
                        if disciplinas_ids:
                            novo_usuario.disciplinas_lecionadas = Disciplina.query.filter(Disciplina.id.in_(disciplinas_ids)).all()
                        if series_ids:
                            novo_usuario.series_lecionadas = Serie.query.filter(Serie.id.in_(series_ids)).all()
                    
                    # Se tudo deu certo até aqui, faz o commit
                    db.session.commit()

                    # AUDITORIA: Registra a criação do novo usuário APÓS o commit bem-sucedido
                    log_audit('USER_CREATE', target_obj=novo_usuario, details={'role': role})
                    
                    flash(f'Usuário {nome} ({role}) criado com sucesso!', 'success')

                except Exception as e:
                    # Em caso de qualquer erro, desfaz todas as operações
                    db.session.rollback()
                    print(f"Erro ao criar usuário: {e}") # Log do erro no console do servidor
                    flash('Ocorreu um erro ao criar o usuário. Tente novamente.', 'danger')

                return redirect(url_for('gerenciar_usuarios'))

    # --- Lógica GET (carregamento da página) ---
    series = Serie.query.filter_by(escola_id=current_user.escola_id).order_by(Serie.nome).all()
    disciplinas = Disciplina.query.filter_by(escola_id=current_user.escola_id).order_by(Disciplina.nome).all()
    # Otimização: Carrega a série atual do aluno junto com a query principal para evitar múltiplas buscas no template
    usuarios = Usuario.query.options(joinedload(Usuario.matriculas).joinedload(Matricula.serie))\
        .filter_by(escola_id=current_user.escola_id).order_by(Usuario.nome).all()

    return render_template('app/gerenciar_usuarios.html', series=series, disciplinas=disciplinas, usuarios=usuarios)

@app.route('/admin/editar_usuario/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('coordenador')
def editar_usuario(user_id):
    # Carrega o usuário e suas associações de forma otimizada
    usuario = Usuario.query.options(
        joinedload(Usuario.disciplinas_lecionadas), 
        joinedload(Usuario.series_lecionadas)
    ).filter_by(id=user_id, escola_id=current_user.escola_id).first_or_404()

    if request.method == 'POST':
        # --- AUDITORIA: Captura o estado do usuário ANTES da alteração ---
        dados_antigos = {
            'nome': usuario.nome,
            'email': usuario.email,
            'disciplinas': [d.nome for d in usuario.disciplinas_lecionadas],
            'series': [s.nome for s in usuario.series_lecionadas]
        }
        alteracoes_realizadas = []

        try:
            # --- Processamento das alterações ---
            novo_nome = request.form.get('nome')
            if novo_nome and novo_nome != usuario.nome:
                usuario.nome = novo_nome
                alteracoes_realizadas.append(f"Nome alterado para '{novo_nome}'")

            novo_email = request.form.get('email')
            if novo_email and novo_email.lower() != usuario.email.lower():
                # Verifica se o novo e-mail já está em uso por OUTRO usuário
                email_existente = Usuario.query.filter(
                    func.lower(Usuario.email) == func.lower(novo_email), 
                    Usuario.id != user_id
                ).first()
                if email_existente:
                    flash('Este e-mail já está sendo utilizado por outro usuário.', 'danger')
                    return redirect(url_for('editar_usuario', user_id=user_id))
                
                usuario.email = novo_email
                alteracoes_realizadas.append(f"Email alterado para '{novo_email}'")

            if usuario.role == 'professor':
                disciplinas_ids = request.form.getlist('disciplinas_ids', type=int)
                series_ids = request.form.getlist('series_ids', type=int)
                
                # Atualiza apenas se houver mudança para registrar na auditoria
                novas_disciplinas = Disciplina.query.filter(Disciplina.id.in_(disciplinas_ids)).all()
                if set(d.id for d in novas_disciplinas) != set(d.id for d in usuario.disciplinas_lecionadas):
                    usuario.disciplinas_lecionadas = novas_disciplinas
                    alteracoes_realizadas.append("Disciplinas lecionadas foram atualizadas.")

                novas_series = Serie.query.filter(Serie.id.in_(series_ids)).all()
                if set(s.id for s in novas_series) != set(s.id for s in usuario.series_lecionadas):
                    usuario.series_lecionadas = novas_series
                    alteracoes_realizadas.append("Séries lecionadas foram atualizadas.")

            nova_senha = request.form.get('senha')
            if nova_senha:
                usuario.password = generate_password_hash(nova_senha, method='pbkdf2:sha256')
                usuario.precisa_trocar_senha = True
                alteracoes_realizadas.append("Senha foi redefinida.")
                flash('Senha redefinida com sucesso! O usuário deverá trocá-la no próximo acesso.', 'info')
            
            # Se alguma alteração foi feita, commita e audita
            if alteracoes_realizadas:
                db.session.commit()
                
                # --- AUDITORIA: Registra o evento de atualização ---
                log_audit(
                    'USER_UPDATE', 
                    target_obj=usuario, 
                    details={'before': dados_antigos, 'changes': alteracoes_realizadas}
                )
                
                flash(f'Usuário {usuario.nome} atualizado com sucesso!', 'success')
            else:
                flash('Nenhuma alteração foi detectada.', 'info')

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar o usuário: {e}', 'danger')
        
        return redirect(url_for('gerenciar_usuarios'))

    # --- Lógica GET (carregamento da página) ---
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
    matricula_atual = None
    if usuario.role == 'aluno' and ano_letivo_ativo:
        matricula_atual = Matricula.query.filter_by(aluno_id=usuario.id, ano_letivo_id=ano_letivo_ativo.id).first()
    
    series_para_select = Serie.query.filter_by(escola_id=current_user.escola_id).order_by(Serie.nome).all()
    series_para_json = [{'id': s.id, 'nome': s.nome} for s in series_para_select]
    disciplinas = Disciplina.query.filter_by(escola_id=current_user.escola_id).order_by(Disciplina.nome).all()
    anos_letivos = AnoLetivo.query.filter_by(escola_id=current_user.escola_id).order_by(AnoLetivo.ano.desc()).all()
    
    return render_template('app/editar_usuario.html', usuario=usuario, series=series_para_select, series_json=series_para_json, disciplinas=disciplinas, matricula_atual=matricula_atual, anos_letivos=anos_letivos)

@app.route('/api/matricula/<int:user_id>/<int:ano_letivo_id>')
@login_required
@role_required('coordenador')
def get_matricula_por_ano(user_id, ano_letivo_id):
    usuario_consultado = Usuario.query.filter_by(id=user_id, escola_id=current_user.escola_id).first()
    if not usuario_consultado:
        return jsonify({'error': 'Usuário não encontrado ou não pertence a esta escola.'}), 404
    matricula = Matricula.query.filter_by(aluno_id=user_id, ano_letivo_id=ano_letivo_id).first()
    if matricula:
        return jsonify({'matriculado': True, 'serie_id': matricula.serie_id, 'status': matricula.status})
    else:
        return jsonify({'matriculado': False})

@app.route('/admin/matricula/salvar', methods=['POST'])
@login_required
@role_required('coordenador')
def salvar_matricula():
    try:
        user_id = request.form.get('user_id', type=int)
        ano_letivo_id = request.form.get('ano_letivo_id', type=int)
        serie_id = request.form.get('serie_id', type=int)
        status = 'cursando'
        if not all([user_id, ano_letivo_id, serie_id]):
            flash('Dados insuficientes para salvar a matrícula. Por favor, selecione a série.', 'danger')
            return redirect(url_for('editar_usuario', user_id=user_id))
        matricula = Matricula.query.filter_by(aluno_id=user_id, ano_letivo_id=ano_letivo_id).first()
        if matricula:
            matricula.serie_id = serie_id
            matricula.status = status
            flash('Matrícula atualizada com sucesso!', 'success')
        else:
            nova_matricula = Matricula(aluno_id=user_id, ano_letivo_id=ano_letivo_id, serie_id=serie_id, status=status)
            db.session.add(nova_matricula)
            flash('Aluno matriculado com sucesso no novo ano letivo!', 'success')
        db.session.commit()
        return redirect(url_for('editar_usuario', user_id=user_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro ao salvar a matrícula: {e}', 'danger')
        return redirect(url_for('gerenciar_usuarios'))

@app.route('/admin/gerenciar-academico', methods=['GET', 'POST'])
@login_required
@role_required('coordenador')
def gerenciar_academico():
    if request.method == 'POST':
        if 'submit_serie' in request.form:
            nome_serie = request.form.get('nome_serie', '').strip()
            if nome_serie:
                serie_existente = Serie.query.filter(db.func.lower(Serie.nome) == db.func.lower(nome_serie), Serie.escola_id == current_user.escola_id).first()
                if not serie_existente:
                    db.session.add(Serie(nome=nome_serie, escola_id=current_user.escola_id))
                    db.session.commit()
                    flash(f'Série "{nome_serie}" cadastrada com sucesso!', 'success')
                else:
                    flash(f'A série "{nome_serie}" já existe nesta escola.', 'danger')
        elif 'submit_disciplina' in request.form:
            nome_disciplina = request.form.get('nome_disciplina', '').strip()
            if nome_disciplina:
                disciplina_existente = Disciplina.query.filter(db.func.lower(Disciplina.nome) == db.func.lower(nome_disciplina), Disciplina.escola_id == current_user.escola_id).first()
                if not disciplina_existente:
                    db.session.add(Disciplina(nome=nome_disciplina, escola_id=current_user.escola_id))
                    db.session.commit()
                    flash(f'Disciplina "{nome_disciplina}" cadastrada com sucesso!', 'success')
                else:
                    flash(f'A disciplina "{nome_disciplina}" já existe nesta escola.', 'danger')
        elif 'submit_associacao' in request.form:
            serie_id = request.form.get('serie_id_assoc')
            if serie_id:
                serie = Serie.query.filter_by(id=serie_id, escola_id=current_user.escola_id).first()
                if serie:
                    disciplinas_ids_selecionadas = request.form.getlist('disciplinas_assoc')
                    disciplinas_selecionadas = Disciplina.query.filter(Disciplina.id.in_(disciplinas_ids_selecionadas), Disciplina.escola_id==current_user.escola_id).all()
                    serie.disciplinas = disciplinas_selecionadas
                    db.session.commit()
                    flash(f'Disciplinas atualizadas para a série "{serie.nome}"!', 'success')
        return redirect(url_for('gerenciar_academico'))
    series = Serie.query.filter_by(escola_id=current_user.escola_id).options(joinedload(Serie.disciplinas)).order_by(Serie.nome).all()
    disciplinas = Disciplina.query.filter_by(escola_id=current_user.escola_id).order_by(Disciplina.nome).all()
    return render_template('app/gerenciar_academico.html', series=series, disciplinas=disciplinas)

# --- Rotas do Banco de Questões ---
@app.route('/professor/criar_questao', methods=['GET', 'POST'])
@login_required
@role_required('professor', 'coordenador')
def criar_questao():
    if request.method == 'POST':
        # Envolve toda a lógica de criação em um bloco try/except
        try:
            disciplina_id = request.form.get('disciplina_id', type=int)
            serie_id = request.form.get('serie_id', type=int)
            assunto = request.form.get('assunto', '').strip()
            tipo = request.form.get('tipo')
            texto = request.form.get('texto')
            justificativa = request.form.get('justificativa_gabarito')
            nivel = request.form.get('nivel')

            # Validação dos dados de entrada
            disciplina = Disciplina.query.filter_by(id=disciplina_id, escola_id=current_user.escola_id).first()
            serie = Serie.query.filter_by(id=serie_id, escola_id=current_user.escola_id).first()
            
            if not all([disciplina, serie, assunto, tipo, texto, nivel]):
                flash('Todos os campos obrigatórios devem ser preenchidos.', 'danger')
                # Redireciona de volta para a página de criação, os dados do GET serão recarregados
                return redirect(url_for('criar_questao'))

            nova_questao = Questao(
                disciplina_id=disciplina_id, 
                serie_id=serie_id, 
                assunto=assunto, 
                tipo=tipo, 
                texto=texto, 
                justificativa_gabarito=justificativa, 
                nivel=nivel,
                criador_id=current_user.id
            )

            # Processamento da imagem
            imagem_arquivo = request.files.get('imagem_questao')
            if imagem_arquivo and allowed_file(imagem_arquivo.filename):
                img = Image.open(imagem_arquivo.stream)
                max_width = 1200
                if img.width > max_width:
                    ratio = max_width / float(img.width)
                    new_height = int(float(img.height) * float(ratio))
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

                original_filename = secure_filename(imagem_arquivo.filename)
                filename_sem_ext, _ = os.path.splitext(original_filename)
                # Adiciona um timestamp para garantir nome de arquivo único
                timestamp = int(datetime.now().timestamp())
                novo_filename = f"{filename_sem_ext}_{timestamp}.webp"
                
                caminho_salvar = os.path.join(app.config['UPLOAD_FOLDER'], novo_filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                img.save(caminho_salvar, 'webp', quality=85)

                nova_questao.imagem_nome = novo_filename
                nova_questao.imagem_alt = request.form.get('imagem_alt')

            # Define as opções com base no tipo de questão
            if tipo == 'multipla_escolha':
                nova_questao.opcao_a = request.form.get('opcao_a')
                nova_questao.opcao_b = request.form.get('opcao_b')
                nova_questao.opcao_c = request.form.get('opcao_c')
                nova_questao.opcao_d = request.form.get('opcao_d')
                nova_questao.gabarito = request.form.get('gabarito_multipla')
            elif tipo == 'verdadeiro_falso':
                nova_questao.opcao_a = 'Verdadeiro'
                nova_questao.opcao_b = 'Falso'
                nova_questao.gabarito = request.form.get('gabarito_vf')

            # Salva no banco de dados
            db.session.add(nova_questao)
            db.session.commit()
            
            # AUDITORIA: Registra a criação da questão APÓS o commit bem-sucedido
            log_audit('QUESTION_CREATE', target_obj=nova_questao, details={'disciplina': disciplina.nome, 'serie': serie.nome, 'assunto': assunto})
            
            flash('Questão criada com sucesso!', 'success')
            return redirect(url_for('banco_questoes'))

        except Exception as e:
            # Em caso de qualquer erro, desfaz a transação e informa o usuário
            db.session.rollback()
            print(f"ERRO AO CRIAR QUESTÃO: {e}") # Log do erro no console do servidor
            flash(f'Ocorreu um erro inesperado ao salvar a questão: {e}', 'danger')
            return redirect(url_for('criar_questao'))

    # --- Lógica GET (carregamento da página) ---
    disciplinas_usuario = []
    series_usuario = []

    if current_user.role == 'coordenador':
        # Coordenador vê todas as disciplinas e séries da escola
        disciplinas_usuario = Disciplina.query.filter_by(escola_id=current_user.escola_id).order_by(Disciplina.nome).all()
        series_usuario = Serie.query.filter_by(escola_id=current_user.escola_id).order_by(Serie.nome).all()
    
    elif current_user.role == 'professor':
        # Professor vê apenas as disciplinas e séries que leciona
        disciplinas_usuario = sorted(current_user.disciplinas_lecionadas, key=lambda d: d.nome)
        series_usuario = sorted(current_user.series_lecionadas, key=lambda s: s.nome)
    
    return render_template('app/criar_questao.html', disciplinas=disciplinas_usuario, series=series_usuario)

@app.route('/professor/banco-questoes')
@login_required
@role_required('professor', 'coordenador')
def banco_questoes():
    questoes = Questao.query.options(joinedload(Questao.disciplina), joinedload(Questao.serie)).filter_by(criador_id=current_user.id).order_by(Questao.id.desc()).all()
    return render_template('app/banco_questoes.html', questoes=questoes)

@app.route('/professor/editar-questao/<int:questao_id>', methods=['GET', 'POST'])
@login_required
@role_required('professor', 'coordenador')
def editar_questao(questao_id):
    # Lógica de permissão aprimorada:
    # Coordenador pode editar qualquer questão da escola.
    # Professor só pode editar as que ele criou.
    query = Questao.query.filter_by(id=questao_id)
    if current_user.role == 'coordenador':
        # Garante que a questão pertence à escola do coordenador
        questao = query.join(Questao.disciplina).filter(Disciplina.escola_id == current_user.escola_id).first_or_404()
    else: # Professor
        questao = query.filter_by(criador_id=current_user.id).first_or_404()

    if request.method == 'POST':
        # --- AUDITORIA: Captura o estado da questão ANTES da alteração ---
        dados_antigos = {
            'disciplina_id': questao.disciplina_id,
            'serie_id': questao.serie_id,
            'assunto': questao.assunto,
            'tipo': questao.tipo,
            'nivel': questao.nivel,
            'texto': questao.texto,
            'gabarito': questao.gabarito
        }
        alteracoes_realizadas = []

        try:
            # --- Processamento das alterações ---
            # Compara cada campo do formulário com o valor existente antes de alterar
            
            novo_disciplina_id = request.form.get('disciplina_id', type=int)
            if novo_disciplina_id != questao.disciplina_id:
                questao.disciplina_id = novo_disciplina_id
                alteracoes_realizadas.append('Disciplina foi alterada.')

            novo_serie_id = request.form.get('serie_id', type=int)
            if novo_serie_id != questao.serie_id:
                questao.serie_id = novo_serie_id
                alteracoes_realizadas.append('Série foi alterada.')

            novo_assunto = request.form.get('assunto', '').strip()
            if novo_assunto != questao.assunto:
                questao.assunto = novo_assunto
                alteracoes_realizadas.append('Assunto foi alterado.')

            novo_nivel = request.form.get('nivel')
            if novo_nivel != questao.nivel:
                questao.nivel = novo_nivel
                alteracoes_realizadas.append(f'Nível alterado para {novo_nivel}.')
            
            novo_texto = request.form.get('texto')
            if novo_texto != questao.texto:
                questao.texto = novo_texto
                alteracoes_realizadas.append('Texto do enunciado foi alterado.')

            questao.justificativa_gabarito = request.form.get('justificativa_gabarito')
            questao.imagem_alt = request.form.get('imagem_alt')

            # Processamento da imagem (com conversão para webp e nome único)
            imagem_arquivo = request.files.get('imagem_questao')
            if imagem_arquivo and allowed_file(imagem_arquivo.filename):
                imagem_antiga = questao.imagem_nome
                
                img = Image.open(imagem_arquivo.stream)
                max_width = 1200
                if img.width > max_width:
                    ratio = max_width / float(img.width)
                    new_height = int(float(img.height) * float(ratio))
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

                original_filename = secure_filename(imagem_arquivo.filename)
                filename_sem_ext, _ = os.path.splitext(original_filename)
                timestamp = int(datetime.now().timestamp())
                novo_filename = f"{filename_sem_ext}_{timestamp}.webp"
                
                caminho_salvar = os.path.join(app.config['UPLOAD_FOLDER'], novo_filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                img.save(caminho_salvar, 'webp', quality=85)

                questao.imagem_nome = novo_filename
                alteracoes_realizadas.append('Imagem foi atualizada.')

                # Remove a imagem antiga para não ocupar espaço
                if imagem_antiga:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], imagem_antiga))
                    except OSError as e:
                        print(f"Erro ao deletar imagem antiga: {e}")

            # Atualiza opções e gabarito com base no tipo
            # O tipo não pode ser alterado na edição para manter a consistência
            if questao.tipo == 'multipla_escolha':
                questao.opcao_a = request.form.get('opcao_a')
                questao.opcao_b = request.form.get('opcao_b')
                questao.opcao_c = request.form.get('opcao_c')
                questao.opcao_d = request.form.get('opcao_d')
                questao.gabarito = request.form.get('gabarito_multipla')
            elif questao.tipo == 'verdadeiro_falso':
                questao.gabarito = request.form.get('gabarito_vf')

            # Se alguma alteração foi feita, commita e audita
            if alteracoes_realizadas or db.session.is_modified(questao):
                db.session.commit()
                
                # --- AUDITORIA: Registra o evento de atualização ---
                log_audit(
                    'QUESTION_UPDATE', 
                    target_obj=questao, 
                    details={'before': dados_antigos, 'changes': alteracoes_realizadas or ['Campos de opções/gabarito foram alterados.']}
                )
                
                flash('Questão atualizada com sucesso!', 'success')
            else:
                flash('Nenhuma alteração foi detectada.', 'info')

            return redirect(url_for('banco_questoes'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar a questão: {e}', 'danger')

    # --- Lógica GET (carregamento da página) ---
    if current_user.role == 'coordenador':
        disciplinas = Disciplina.query.filter_by(escola_id=current_user.escola_id).order_by(Disciplina.nome).all()
        series = Serie.query.filter_by(escola_id=current_user.escola_id).order_by(Serie.nome).all()
    else: # Professor
        disciplinas = sorted(current_user.disciplinas_lecionadas, key=lambda d: d.nome)
        series = sorted(current_user.series_lecionadas, key=lambda s: s.nome)
        
    return render_template('app/editar_questao.html', questao=questao, disciplinas=disciplinas, series=series)

# --- Rotas de Avaliação ---
@app.route('/criar-modelo-avaliacao', methods=['GET', 'POST'])
@login_required
@role_required('coordenador', 'professor')
def criar_modelo_avaliacao():
    if request.method == 'POST':
        # Envolve toda a lógica de criação em um bloco try/except para garantir a integridade dos dados
        try:
            nome_modelo = request.form.get('nome_modelo')
            serie_id = request.form.get('serie_id', type=int)
            tipo_modelo = request.form.get('tipo_modelo')
            tempo_limite_str = request.form.get('tempo_limite')
            tempo_limite = int(tempo_limite_str) if tempo_limite_str and tempo_limite_str.isdigit() else None

            # Validação inicial
            if not all([nome_modelo, serie_id, tipo_modelo]):
                flash('Nome, série e tipo do modelo são obrigatórios.', 'danger')
                return redirect(url_for('criar_modelo_avaliacao'))

            regras_json = {'tipo': tipo_modelo, 'disciplinas': []}
            total_questoes_modelo = 0

            # Lógica para PROVA
            if tipo_modelo == 'prova':
                disciplina_id = request.form.get('disciplina_id', type=int)
                assuntos = request.form.getlist('assuntos')
                niveis = {
                    'facil': request.form.get('qtd_facil', type=int, default=0),
                    'media': request.form.get('qtd_media', type=int, default=0),
                    'dificil': request.form.get('qtd_dificil', type=int, default=0)
                }
                total_questoes_disciplina = sum(niveis.values())
                
                if total_questoes_disciplina <= 0 or not assuntos:
                    flash('Para uma prova, você deve selecionar ao menos um assunto e especificar pelo menos uma questão.', 'danger')
                    return redirect(url_for('criar_modelo_avaliacao'))
                
                regras_json['disciplinas'].append({
                    'id': disciplina_id,
                    'assuntos': assuntos,
                    'niveis': niveis
                })
                total_questoes_modelo = total_questoes_disciplina

            # Lógica para SIMULADO
            elif tipo_modelo == 'simulado':
                disciplinas_selecionadas_ids = request.form.getlist('disciplinas_selecionadas')
                if not disciplinas_selecionadas_ids:
                    flash('Você deve selecionar pelo menos uma disciplina para o simulado.', 'danger')
                    return redirect(url_for('criar_modelo_avaliacao'))

                for disc_id_str in disciplinas_selecionadas_ids:
                    disc_id = int(disc_id_str)
                    assuntos = request.form.getlist(f'assuntos_disciplina_{disc_id}')
                    niveis = {
                        'facil': request.form.get(f'qtd_facil_disciplina_{disc_id}', type=int, default=0),
                        'media': request.form.get(f'qtd_media_disciplina_{disc_id}', type=int, default=0),
                        'dificil': request.form.get(f'qtd_dificil_disciplina_{disc_id}', type=int, default=0)
                    }
                    total_questoes_disciplina = sum(niveis.values())
                    
                    if total_questoes_disciplina > 0 and assuntos:
                        regras_json['disciplinas'].append({
                            'id': disc_id,
                            'assuntos': assuntos,
                            'niveis': niveis
                        })
                        total_questoes_modelo += total_questoes_disciplina
            
            # Validação final: garante que o modelo não está vazio
            if not regras_json['disciplinas']:
                 flash('Nenhuma regra válida foi definida. Verifique as quantidades de questões e os assuntos marcados.', 'danger')
                 return redirect(url_for('criar_modelo_avaliacao'))

            # Cria o objeto do modelo
            novo_modelo = ModeloAvaliacao(
                nome=nome_modelo,
                tipo=tipo_modelo,
                serie_id=serie_id,
                tempo_limite=tempo_limite,
                escola_id=current_user.escola_id,
                criador_id=current_user.id,
                regras_selecao=regras_json
            )
            
            db.session.add(novo_modelo)
            db.session.commit()
            
            # --- AUDITORIA: Registra a criação do modelo APÓS o commit ---
            serie = Serie.query.get(serie_id)
            log_audit(
                'ASSESSMENT_MODEL_CREATE', 
                target_obj=novo_modelo, 
                details={
                    'nome': nome_modelo,
                    'tipo': tipo_modelo,
                    'serie': serie.nome,
                    'total_questoes': total_questoes_modelo
                }
            )
            
            flash(f'Modelo de avaliação "{nome_modelo}" criado com sucesso!', 'success')
            return redirect(url_for('listar_modelos_avaliacao'))

        except Exception as e:
            db.session.rollback()
            print(f"ERRO AO CRIAR MODELO DE AVALIAÇÃO: {e}")
            flash(f'Ocorreu um erro inesperado ao salvar o modelo: {e}', 'danger')
            return redirect(url_for('criar_modelo_avaliacao'))

    # --- Lógica GET (carregamento da página) ---
    series_query = []
    disciplinas_query = []

    if current_user.role == 'coordenador':
        series_query = Serie.query.filter_by(escola_id=current_user.escola_id).order_by(Serie.nome).all()
        disciplinas_query = Disciplina.query.filter_by(escola_id=current_user.escola_id).order_by(Disciplina.nome).all()
    
    elif current_user.role == 'professor':
        series_query = sorted(current_user.series_lecionadas, key=lambda s: s.nome)
        disciplinas_query = sorted(current_user.disciplinas_lecionadas, key=lambda d: d.nome)

    series_list = [{'id': s.id, 'nome': s.nome} for s in series_query]
    disciplinas_list = [{'id': d.id, 'nome': d.nome} for d in disciplinas_query]
    disciplinas_json_string = json.dumps(disciplinas_list)
    
    return render_template(
        'app/criar_modelo_avaliacao.html', 
        series=series_list, 
        disciplinas_json=disciplinas_json_string
    )

@app.route('/iniciar-avaliacao/<int:modelo_id>')
@login_required
@role_required('aluno')
def iniciar_avaliacao_dinamica(modelo_id):
    modelo = ModeloAvaliacao.query.get_or_404(modelo_id)
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
    avaliacao_existente = Avaliacao.query.join(Resultado).filter(Avaliacao.modelo_id == modelo_id, Avaliacao.is_dinamica == True, Resultado.aluno_id == current_user.id, Resultado.status != 'Finalizado').first()
    if avaliacao_existente:
        return redirect(url_for('responder_avaliacao', avaliacao_id=avaliacao_existente.id))
    regras = modelo.regras_selecao
    questoes_selecionadas = []
    disciplinas_incluidas_simulado = []
    for regra_disciplina in regras['disciplinas']:
        disciplina_id = regra_disciplina['id']
        assuntos = regra_disciplina['assuntos']
        disciplinas_incluidas_simulado.append(Disciplina.query.get(disciplina_id))
        for nivel, quantidade in regra_disciplina['niveis'].items():
            if quantidade > 0:
                questoes_disponiveis = Questao.query.filter(Questao.disciplina_id == disciplina_id, Questao.serie_id == modelo.serie_id, Questao.assunto.in_(assuntos), Questao.nivel == nivel).all()
                if len(questoes_disponiveis) < quantidade:
                    flash(f"Não há questões suficientes (nível: {nivel}, disciplina: {Disciplina.query.get(disciplina_id).nome}) para gerar sua avaliação. Contate o professor.", "danger")
                    return redirect(url_for('listar_modelos_avaliacao'))
                questoes_selecionadas.extend(random.sample(questoes_disponiveis, quantidade))
    if not questoes_selecionadas:
        flash("Não foi possível gerar a avaliação pois nenhuma questão foi encontrada com as regras definidas.", "danger")
        return redirect(url_for('listar_modelos_avaliacao'))
    random.shuffle(questoes_selecionadas)
    nova_avaliacao = Avaliacao(nome=f"{modelo.nome} - {current_user.nome}", tipo=modelo.tipo, serie_id=modelo.serie_id, disciplina_id=regras['disciplinas'][0]['id'] if modelo.tipo == 'prova' else None, criador_id=modelo.criador_id, escola_id=modelo.escola_id, ano_letivo_id=ano_letivo_ativo.id, is_dinamica=True, modelo_id=modelo.id)
    if modelo.tipo == 'simulado':
        nova_avaliacao.disciplinas_simulado = disciplinas_incluidas_simulado
    nova_avaliacao.questoes = questoes_selecionadas
    novo_resultado = Resultado(aluno_id=current_user.id, avaliacao=nova_avaliacao, ano_letivo_id=ano_letivo_ativo.id, status="Iniciada")
    db.session.add(nova_avaliacao)
    db.session.add(novo_resultado)
    db.session.commit()
    return redirect(url_for('responder_avaliacao', avaliacao_id=nova_avaliacao.id))

@app.route('/modelos-avaliacoes')
@login_required
@role_required('aluno', 'professor', 'coordenador')
def listar_modelos_avaliacao():
    """
    Exibe as avaliações disponíveis para o usuário logado.
    - Para Alunos: Mostra os modelos que eles podem iniciar.
    - Para Professores/Coordenadores: Mostra as avaliações já geradas para gerenciamento.
    """
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
    if not ano_letivo_ativo:
        flash('Nenhum ano letivo ativo configurado. Contate o coordenador.', 'warning')
        if current_user.role in ['coordenador', 'professor']:
             return render_template('app/listar_avaliacoes_geradas.html', avaliacoes=[])
        else:
             return render_template('app/listar_modelos_avaliacao.html', modelos=[], recuperacoes=[], ids_concluidas=set())

    # --- Lógica para Professores e Coordenadores ---

    if current_user.role == 'coordenador':
        # Coordenador vê todas as avaliações GERADAS da escola no ano ativo
        avaliacoes_geradas = Avaliacao.query.options(
            joinedload(Avaliacao.serie),
            joinedload(Avaliacao.criador)
        ).filter(
            Avaliacao.escola_id == current_user.escola_id,
            Avaliacao.ano_letivo_id == ano_letivo_ativo.id
        ).order_by(Avaliacao.id.desc()).all()
        return render_template('app/listar_avaliacoes_geradas.html', avaliacoes=avaliacoes_geradas)
    
    elif current_user.role == 'professor':
        # Professor vê apenas as avaliações que ele mesmo criou no ano ativo
        # CORREÇÃO: Corrigido o erro de digitação de 'Avaliaco' para 'Avaliacao'
        avaliacoes_geradas = Avaliacao.query.options(
            joinedload(Avaliacao.serie), # <--- CORRIGIDO AQUI
            joinedload(Avaliacao.criador)
        ).filter(
            Avaliacao.criador_id == current_user.id,
            Avaliacao.escola_id == current_user.escola_id,
            Avaliacao.ano_letivo_id == ano_letivo_ativo.id
        ).order_by(Avaliacao.id.desc()).all()
        return render_template('app/listar_avaliacoes_geradas.html', avaliacoes=avaliacoes_geradas)
    
    # --- Lógica para o Aluno (continua a mesma) ---

    elif current_user.role == 'aluno':
        modelos = []
        ids_concluidas = set()
        recuperacoes_designadas = []
        
        serie_aluno = current_user.serie_atual
        if not serie_aluno:
            flash('Você não está matriculado em nenhuma série no ano letivo ativo.', 'warning')
            return redirect(url_for('dashboard'))
        
        modelos_da_serie = ModeloAvaliacao.query.filter_by(serie_id=serie_aluno.id).order_by(ModeloAvaliacao.id.desc()).all()
        modelos.extend(modelos_da_serie)

        recuperacoes_designadas = current_user.avaliacoes_designadas
        modelos.extend(recuperacoes_designadas)

        resultados_finalizados_dinamicos = db.session.query(Avaliacao.modelo_id).join(Resultado).filter(
            Resultado.aluno_id == current_user.id, Resultado.status == 'Finalizado',
            Avaliacao.is_dinamica == True, Avaliacao.modelo_id.isnot(None)
        ).distinct().all()
        ids_concluidas.update([r.modelo_id for r in resultados_finalizados_dinamicos])

        resultados_finalizados_recuperacao = db.session.query(Resultado.avaliacao_id).filter(
            Resultado.aluno_id == current_user.id, Resultado.status == 'Finalizado',
            Resultado.avaliacao.has(tipo='recuperacao')
        ).distinct().all()
        ids_concluidas.update([r.avaliacao_id for r in resultados_finalizados_recuperacao])
        
        return render_template('app/listar_modelos_avaliacao.html',
                               modelos=modelos,
                               recuperacoes=recuperacoes_designadas,
                               ids_concluidas=ids_concluidas)

@app.route('/criar-recuperacao', methods=['GET', 'POST'])
@login_required
@role_required('professor', 'coordenador')
def criar_recuperacao():
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
    if not ano_letivo_ativo:
        flash('Não é possível criar avaliações sem um ano letivo ativo.', 'warning')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        nome_avaliacao = request.form.get('nome_avaliacao')
        disciplina_id = request.form.get('disciplina_id', type=int)
        serie_id = request.form.get('serie_id', type=int)
        alunos_ids = request.form.getlist('alunos_ids', type=int)
        if not all([nome_avaliacao, disciplina_id, serie_id, alunos_ids]):
            flash('Nome, disciplina, série e ao menos um aluno são obrigatórios.', 'danger')
            return redirect(url_for('criar_recuperacao'))
        qtd_facil = request.form.get('qtd_facil', type=int, default=0)
        qtd_media = request.form.get('qtd_media', type=int, default=0)
        qtd_dificil = request.form.get('qtd_dificil', type=int, default=0)
        assuntos = request.form.getlist('assuntos')
        questoes_selecionadas = []
        alunos_selecionados = Usuario.query.filter(Usuario.id.in_(alunos_ids)).all()
        nova_recuperacao = Avaliacao(nome=nome_avaliacao, tipo='recuperacao', disciplina_id=disciplina_id, serie_id=serie_id, criador_id=current_user.id, escola_id=current_user.escola_id, ano_letivo_id=ano_letivo_ativo.id, is_dinamica=False)
        nova_recuperacao.questoes = questoes_selecionadas
        nova_recuperacao.alunos_designados = alunos_selecionados
        db.session.add(nova_recuperacao)
        db.session.commit()
        flash(f'Prova de recuperação "{nome_avaliacao}" criada e designada com sucesso!', 'success')
        return redirect(url_for('listar_avaliacoes'))
    series = Serie.query.filter_by(escola_id=current_user.escola_id).order_by(Serie.nome).all()
    disciplinas = Disciplina.query.filter_by(escola_id=current_user.escola_id).order_by(Disciplina.nome).all()
    return render_template('app/criar_recuperacao.html', series=series, disciplinas=disciplinas)

@app.route('/avaliacoes')
@login_required
def listar_avaliacoes():
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
    if not ano_letivo_ativo:
        flash('Nenhum ano letivo ativo configurado para sua escola. Por favor, contate o coordenador.', 'warning')
        return render_template('app/listar_avaliacoes.html', avaliacoes=[], ids_concluidas=set())
    avaliacoes = []
    ids_concluidas = set()
    if current_user.role == 'aluno':
        ids_concluidas = {r.avaliacao_id for r in Resultado.query.filter_by(aluno_id=current_user.id).all()}
        matricula_ativa = Matricula.query.filter_by(aluno_id=current_user.id, ano_letivo_id=ano_letivo_ativo.id).first()
        if matricula_ativa:
            avaliacoes = Avaliacao.query.filter_by(serie_id=matricula_ativa.serie_id, ano_letivo_id=ano_letivo_ativo.id).order_by(Avaliacao.id.desc()).all()
    elif current_user.role == 'professor':
        avaliacoes = Avaliacao.query.filter_by(escola_id=current_user.escola_id, ano_letivo_id=ano_letivo_ativo.id, criador_id=current_user.id).order_by(Avaliacao.id.desc()).all()
    elif current_user.role == 'coordenador':
        avaliacoes = Avaliacao.query.filter_by(escola_id=current_user.escola_id, ano_letivo_id=ano_letivo_ativo.id).order_by(Avaliacao.id.desc()).all()
    return render_template('app/listar_avaliacoes.html', avaliacoes=avaliacoes, ids_concluidas=ids_concluidas)

@app.route('/avaliacao/<int:avaliacao_id>/detalhes')
@login_required
@role_required('coordenador', 'professor')
def detalhes_avaliacao(avaliacao_id):
    avaliacao = Avaliacao.query.filter_by(id=avaliacao_id, escola_id=current_user.escola_id).first_or_404()
    resultados = Resultado.query.filter_by(avaliacao_id=avaliacao.id).options(joinedload(Resultado.aluno)).order_by(Resultado.nota.desc().nullslast()).all()
    num_participantes = len(resultados)
    notas_validas = [r.nota for r in resultados if r.nota is not None]
    soma_notas = sum(notas_validas)
    media_turma = round(soma_notas / len(notas_validas), 2) if notas_validas else 0.0
    return render_template('app/detalhes_avaliacao.html', avaliacao=avaliacao, resultados=resultados, num_participantes=num_participantes, media_turma=media_turma)

@app.route('/meus-resultados')
@login_required
@role_required('aluno')
def meus_resultados():
    # 1. Busca todos os resultados do aluno que foram 'Finalizado' ou 'Pendente'
    resultados_aluno = Resultado.query.options(
        joinedload(Resultado.avaliacao).joinedload(Avaliacao.disciplina)
    ).filter(
        Resultado.aluno_id == current_user.id,
        Resultado.status.in_(['Finalizado', 'Pendente'])
    ).order_by(Resultado.data_realizacao.desc()).all()

    # ... (O restante da lógica para 'Provas' e 'Simulados' continua igual)
    resultados_provas = [r for r in resultados_aluno if r.avaliacao.tipo == 'prova']
    total_provas = len(resultados_provas)
    soma_notas_provas = sum(r.nota for r in resultados_provas if r.nota is not None)
    media_provas = round(soma_notas_provas / total_provas, 1) if total_provas > 0 else 0.0
    chart_labels_provas = [res.avaliacao.nome for res in reversed(resultados_provas)]
    chart_data_provas = [res.nota for res in reversed(resultados_provas)]

    resultados_simulados = [r for r in resultados_aluno if r.avaliacao.tipo == 'simulado']
    total_simulados = len(resultados_simulados)
    soma_notas_simulados = sum(r.nota for r in resultados_simulados if r.nota is not None)
    media_simulados = round(soma_notas_simulados / total_simulados, 1) if total_simulados > 0 else 0.0
    chart_labels_simulados = [res.avaliacao.nome for res in reversed(resultados_simulados)]
    chart_data_simulados = [res.nota for res in reversed(resultados_simulados)]

    # --- Lógica para a aba 'Desempenho por Disciplina' ---
    dados_por_disciplina = {}
    for res in resultados_provas:
        if res.nota is None or not res.avaliacao.disciplina:
            continue
        disciplina_nome = res.avaliacao.disciplina.nome
        if disciplina_nome not in dados_por_disciplina:
            dados_por_disciplina[disciplina_nome] = {'soma_notas': 0.0, 'quantidade': 0, 'media': 0.0, 'avaliacoes': []}
        
        dados_por_disciplina[disciplina_nome]['soma_notas'] += res.nota
        dados_por_disciplina[disciplina_nome]['quantidade'] += 1
        
        # CORREÇÃO: Adicionamos o 'id' do resultado aqui
        dados_por_disciplina[disciplina_nome]['avaliacoes'].append({
            "id": res.id, # <--- ADICIONADO AQUI
            "nome": res.avaliacao.nome,
            "nota": res.nota,
            "data": res.data_realizacao.strftime('%d/%m/%Y')
        })

    for nome, dados in dados_por_disciplina.items():
        if dados['quantidade'] > 0:
            dados['media'] = round(dados['soma_notas'] / dados['quantidade'], 1)

    return render_template(
        'app/meus_resultados.html', 
        dados_por_disciplina=dados_por_disciplina,
        total_provas=total_provas,
        media_provas=media_provas,
        chart_labels_provas=chart_labels_provas,
        chart_data_provas=chart_data_provas,
        total_simulados=total_simulados,
        media_simulados=media_simulados,
        chart_labels_simulados=chart_labels_simulados,
        chart_data_simulados=chart_data_simulados
    )

@app.route('/resultado/<int:resultado_id>')
@login_required
@role_required('aluno')
def ver_resultado_detalhado(resultado_id):
    """
    Exibe a prova corrigida para o aluno, incluindo feedbacks.
    """
    # CORREÇÃO: Ajustamos a query para não tentar fazer o joinedload em 'respostas'
    # que é uma relação dinâmica. As outras otimizações continuam.
    resultado = Resultado.query.options(
        joinedload(Resultado.avaliacao).joinedload(Avaliacao.criador)
    ).filter_by(id=resultado_id).first_or_404()

    # GARANTIA DE SEGURANÇA: Verifica se o resultado pertence ao aluno logado
    if resultado.aluno_id != current_user.id:
        abort(403) # Proíbe o acesso se não for o dono da prova

    # O template 'ver_resultado.html' que já criamos continua o mesmo.
    # Ele acessará 'resultado.respostas' que funcionará corretamente.
    return render_template('app/ver_resultado.html', resultado=resultado)

@app.route('/correcao/avaliacao/<int:avaliacao_id>')
@login_required
@role_required('professor', 'coordenador')
def correcao_lista_alunos(avaliacao_id):
    avaliacao = Avaliacao.query.get_or_404(avaliacao_id)
    resultados_pendentes = Resultado.query.filter_by(avaliacao_id=avaliacao.id, status='Pendente').all()
    return render_template('app/correcao_lista.html', avaliacao=avaliacao, resultados=resultados_pendentes)

@app.route('/correcao/resultado/<int:resultado_id>', methods=['GET', 'POST'])
@login_required
@role_required('professor', 'coordenador')
def corrigir_respostas(resultado_id):
    # Otimiza a query para carregar todas as informações necessárias de uma vez
    resultado = Resultado.query.options(
        joinedload(Resultado.aluno),
        joinedload(Resultado.avaliacao).joinedload(Avaliacao.questoes),
        joinedload(Resultado.respostas).joinedload(Resposta.questao)
    ).filter(Resultado.id == resultado_id).first_or_404()

    # --- Verificação de Segurança e Permissão ---
    # Garante que o professor/coordenador pertence à mesma escola do resultado
    if resultado.avaliacao.escola_id != current_user.escola_id:
        abort(403) # Acesso Proibido
    # Garante que um professor só pode corrigir avaliações que ele criou
    if current_user.role == 'professor' and resultado.avaliacao.criador_id != current_user.id:
        flash('Você não tem permissão para corrigir esta avaliação, pois não é o criador.', 'danger')
        return redirect(url_for('listar_modelos_avaliacao'))
    # Impede a re-correção de uma prova já finalizada
    if resultado.status == 'Finalizado':
        flash('Esta avaliação já foi corrigida e finalizada.', 'info')
        return redirect(url_for('detalhes_avaliacao', avaliacao_id=resultado.avaliacao_id))

    if request.method == 'POST':
        # Envolve toda a lógica de correção em um bloco try/except
        try:
            # Itera apenas sobre as respostas discursivas para aplicar a correção manual
            for resposta in resultado.respostas:
                if resposta.questao.tipo == 'discursiva':
                    status = request.form.get(f'status_{resposta.id}')
                    feedback = request.form.get(f'feedback_{resposta.id}')
                    
                    if status:
                        resposta.status_correcao = status
                        resposta.feedback_professor = feedback
                        if status == 'correta':
                            resposta.pontos = 1.0
                        elif status == 'parcial':
                            resposta.pontos = 0.5
                        else: # 'incorreta'
                            resposta.pontos = 0.0
            
            # Recalcula a nota final somando os pontos de TODAS as respostas (objetivas + discursivas)
            total_pontos = sum(r.pontos for r in resultado.respostas)
            total_questoes = len(resultado.avaliacao.questoes)
            nota_final = round((total_pontos / total_questoes) * 10, 2) if total_questoes > 0 else 0
            
            # Atualiza o resultado com a nova nota e o status final
            resultado.nota = nota_final
            resultado.status = 'Finalizado'
            
            db.session.commit()

            # --- AUDITORIA: Registra a finalização da correção APÓS o commit ---
            log_audit(
                'GRADING_COMPLETED',
                target_obj=resultado.avaliacao,
                details={
                    'aluno_id': resultado.aluno_id,
                    'aluno_nome': resultado.aluno.nome,
                    'resultado_id': resultado.id,
                    'nota_final': nota_final
                }
            )

            flash(f'Correção salva com sucesso! A nota final do aluno {resultado.aluno.nome} é {nota_final}.', 'success')
            return redirect(url_for('detalhes_avaliacao', avaliacao_id=resultado.avaliacao_id))

        except Exception as e:
            db.session.rollback()
            print(f"ERRO AO CORRIGIR RESPOSTAS: {e}")
            flash(f'Ocorreu um erro inesperado ao salvar a correção: {e}', 'danger')
            return redirect(url_for('corrigir_respostas', resultado_id=resultado_id))

    # --- Lógica GET (carregamento da página) ---
    # Filtra as respostas discursivas para exibir na página
    respostas_discursivas = [r for r in resultado.respostas if r.questao.tipo == 'discursiva']
    
    return render_template('app/correcao_respostas.html', resultado=resultado, respostas=respostas_discursivas)

@app.route('/admin/relatorios')
@login_required
@role_required('coordenador')
def painel_relatorios():
    series = Serie.query.filter_by(escola_id=current_user.escola_id).order_by(Serie.nome).all()
    simulados = Avaliacao.query.filter_by(escola_id=current_user.escola_id, tipo='simulado').order_by(Avaliacao.id.desc()).all()
    anos_letivos = AnoLetivo.query.filter_by(escola_id=current_user.escola_id).order_by(AnoLetivo.ano.desc()).all()
    disciplinas = Disciplina.query.filter_by(escola_id=current_user.escola_id).order_by(Disciplina.nome).all()
    avaliacoes = Avaliacao.query.filter_by(escola_id=current_user.escola_id).order_by(Avaliacao.nome).all()
    return render_template('app/painel_relatorios.html', series=series, simulados=simulados, anos_letivos=anos_letivos, disciplinas=disciplinas, avaliacoes=avaliacoes)

@app.route('/admin/auditoria')
@login_required
@role_required('coordenador')
def painel_auditoria():
    page = request.args.get('page', 1, type=int)
    
    # Filtros do formulário
    action_filter = request.args.get('action')
    user_filter = request.args.get('user')
    
    # --- CORREÇÃO ---
    # 1. Pega a lista de todos os e-mails de usuários da escola do coordenador.
    # Isso é mais seguro do que usar JOINs que podem falhar com logs de sistema ou usuários deletados.
    emails_da_escola = db.session.query(Usuario.email).filter(Usuario.escola_id == current_user.escola_id).scalar_subquery()
    
    # 2. Filtra os logs para mostrar apenas aqueles cujo user_email está na lista de e-mails da escola.
    query = AuditLog.query.filter(AuditLog.user_email.in_(emails_da_escola))
    
    # 3. Aplica os filtros do formulário sobre o resultado inicial.
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    if user_filter:
        query = query.filter(AuditLog.user_email.ilike(f'%{user_filter}%'))

    # 4. Ordena e pagina os resultados.
    logs = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=20, error_out=False)
    
    # Para popular o dropdown de filtros, busca ações distintas apenas dos logs da escola.
    distinct_actions_query = query.with_entities(AuditLog.action).distinct().order_by(AuditLog.action)
    actions = [a[0] for a in distinct_actions_query.all()]

    return render_template('app/painel_auditoria.html', logs=logs, actions=actions, action_filter=action_filter, user_filter=user_filter)

@app.route('/admin/relatorios/desempenho_por_assunto', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_desempenho_por_assunto():
    serie_id = request.form.get('serie_id', type=int)
    disciplina_id = request.form.get('disciplina_id', type=int)
    if not serie_id or not disciplina_id:
        flash('Você precisa selecionar uma série e uma disciplina.', 'warning')
        return redirect(url_for('painel_relatorios'))
    serie = Serie.query.get(serie_id)
    disciplina = Disciplina.query.get(disciplina_id)
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
    if not ano_letivo_ativo:
        flash('Nenhum ano letivo ativo encontrado.', 'danger')
        return redirect(url_for('painel_relatorios'))
    alunos_ids = [m.aluno_id for m in Matricula.query.filter_by(serie_id=serie_id, ano_letivo_id=ano_letivo_ativo.id).all()]
    if not alunos_ids:
        flash('Nenhum aluno encontrado nesta série para o ano letivo ativo.', 'info')
        return redirect(url_for('painel_relatorios'))
    resultados_por_assunto = db.session.query(Questao.assunto, func.avg(Resposta.pontos) * 10, func.count(Resposta.id)).join(Questao, Resposta.questao_id == Questao.id).join(Resultado, Resposta.resultado_id == Resultado.id).filter(Questao.disciplina_id == disciplina_id, Resultado.aluno_id.in_(alunos_ids)).group_by(Questao.assunto).order_by(Questao.assunto).all()
    html_renderizado = render_template('app/relatorios/desempenho_por_assunto.html', serie=serie, disciplina=disciplina, ano_letivo=ano_letivo_ativo, dados=resultados_por_assunto, data_geracao=datetime.now())
    pdf = HTML(string=html_renderizado).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=relatorio_desempenho_por_assunto.pdf'
    return response

@app.route('/admin/relatorios/desempenho_por_nivel', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_desempenho_por_nivel():
    serie_id = request.form.get('serie_id', type=int)
    aluno_id = request.form.get('aluno_id', type=int)
    if not serie_id:
        flash('Você precisa selecionar uma série.', 'warning')
        return redirect(url_for('painel_relatorios'))
    serie = Serie.query.get(serie_id)
    aluno = Usuario.query.get(aluno_id) if aluno_id else None
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
    if aluno:
        aluno_ids = [aluno.id]
    else:
        aluno_ids = [m.aluno_id for m in Matricula.query.filter_by(serie_id=serie_id, ano_letivo_id=ano_letivo_ativo.id).all()]
    if not aluno_ids:
        flash('Nenhum aluno encontrado para os filtros selecionados.', 'info')
        return redirect(url_for('painel_relatorios'))
    dados_por_nivel = db.session.query(Questao.nivel, func.avg(Resposta.pontos) * 10, func.count(Resposta.id)).join(Questao, Resposta.questao_id == Questao.id).join(Resultado, Resposta.resultado_id == Resultado.id).filter(Resultado.aluno_id.in_(aluno_ids)).group_by(Questao.nivel).order_by(Questao.nivel).all()
    html_renderizado = render_template('app/relatorios/desempenho_por_nivel.html', serie=serie, aluno=aluno, dados=dados_por_nivel, data_geracao=datetime.now())
    pdf = HTML(string=html_renderizado).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=relatorio_desempenho_por_nivel.pdf'
    return response

@app.route('/admin/relatorios/analise_de_itens', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_analise_de_itens():
    avaliacao_id = request.form.get('avaliacao_id', type=int)
    if not avaliacao_id:
        flash('Você precisa selecionar uma avaliação.', 'warning')
        return redirect(url_for('painel_relatorios'))
    avaliacao = Avaliacao.query.options(joinedload(Avaliacao.questoes)).get_or_404(avaliacao_id)
    respostas = Resposta.query.join(Resultado).filter(Resultado.avaliacao_id == avaliacao.id).all()
    if not respostas:
        flash('Nenhuma resposta encontrada para esta avaliação.', 'info')
        return redirect(url_for('painel_relatorios'))
    analise_dados = {}
    for questao in avaliacao.questoes:
        analise_dados[questao.id] = {'questao_obj': questao, 'total_respostas': 0, 'acertos': 0, 'distratores': {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'Outros': 0}}
    for resposta in respostas:
        if resposta.questao_id in analise_dados:
            dados_questao = analise_dados[resposta.questao_id]
            dados_questao['total_respostas'] += 1
            if resposta.pontos == 1.0:
                dados_questao['acertos'] += 1
            if resposta.resposta_aluno in dados_questao['distratores']:
                dados_questao['distratores'][resposta.resposta_aluno] += 1
            else:
                dados_questao['distratores']['Outros'] += 1
    html_renderizado = render_template('app/relatorios/analise_de_itens.html', avaliacao=avaliacao, analise_dados=analise_dados, data_geracao=datetime.now())
    pdf = HTML(string=html_renderizado).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=relatorio_analise_itens_{avaliacao.id}.pdf'
    return response

@app.route('/admin/relatorios/saude_banco_questoes')
@login_required
@role_required('coordenador')
def relatorio_saude_banco_questoes():
    # --- Query Corrigida ---
    # O erro foi corrigido na cláusula .filter()
    dados_brutos = db.session.query(
        Disciplina.nome,
        Questao.tipo,
        Questao.nivel,
        func.count(Questao.id)
    ).join(Disciplina, Questao.disciplina_id == Disciplina.id)\
     .filter(Disciplina.escola_id == current_user.escola_id)\
     .group_by(Disciplina.nome, Questao.tipo, Questao.nivel)\
     .order_by(Disciplina.nome, Questao.nivel, Questao.tipo)\
     .all()

    # Processa os dados brutos em um formato mais amigável para o template
    relatorio_processado = {}
    total_geral = 0
    for nome_disciplina, tipo, nivel, quantidade in dados_brutos:
        total_geral += quantidade
        if nome_disciplina not in relatorio_processado:
            relatorio_processado[nome_disciplina] = {'total': 0, 'detalhes': []}
        
        relatorio_processado[nome_disciplina]['total'] += quantidade
        relatorio_processado[nome_disciplina]['detalhes'].append({
            'tipo': tipo.replace('_', ' ').capitalize(),
            'nivel': nivel.capitalize(),
            'quantidade': quantidade
        })

    # Renderiza o template do relatório
    html_renderizado = render_template(
        'app/relatorios/saude_banco_questoes.html',
        dados=relatorio_processado,
        total_geral=total_geral,
        data_geracao=datetime.now()
    )
    
    # Gera o PDF
    pdf = HTML(string=html_renderizado).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=relatorio_saude_banco_questoes.pdf'
    return response

@app.route('/admin/relatorios/comparativo_turmas', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_comparativo_turmas():
    avaliacao_id = request.form.get('avaliacao_id', type=int)
    if not avaliacao_id:
        flash('Você precisa selecionar uma avaliação.', 'warning')
        return redirect(url_for('painel_relatorios'))
    avaliacao = Avaliacao.query.get_or_404(avaliacao_id)
    dados_comparativos = db.session.query(Serie.nome, func.count(Resultado.id).label('num_participantes'), func.avg(Resultado.nota).label('media_turma')).join(Matricula, Resultado.aluno_id == Matricula.aluno_id).join(Serie, Matricula.serie_id == Serie.id).filter(Resultado.avaliacao_id == avaliacao_id, Matricula.ano_letivo_id == avaliacao.ano_letivo_id).group_by(Serie.nome).order_by(func.avg(Resultado.nota).desc()).all()
    if not dados_comparativos:
        flash('Não há dados de diferentes turmas para comparar para esta avaliação.', 'info')
        return redirect(url_for('painel_relatorios'))
    html_renderizado = render_template('app/relatorios/comparativo_turmas.html', avaliacao=avaliacao, dados=dados_comparativos, data_geracao=datetime.now())
    pdf = HTML(string=html_renderizado).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=relatorio_comparativo_turmas_{avaliacao.id}.pdf'
    return response

@app.route('/admin/relatorios/alunos_por_serie', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_alunos_por_serie():
    series_ids_str = request.form.getlist('series_ids')
    ano_letivo_id = request.form.get('ano_letivo_id', type=int)

    if not series_ids_str or not ano_letivo_id:
        flash('Você precisa selecionar pelo menos uma série e um ano letivo.', 'warning')
        return redirect(url_for('painel_relatorios'))
    
    try:
        series_ids_int = [int(sid) for sid in series_ids_str]
    except ValueError:
        flash('Ocorreu um erro ao processar as séries selecionadas.', 'danger')
        return redirect(url_for('painel_relatorios'))

    ano_letivo = AnoLetivo.query.get(ano_letivo_id)
    
    # --- CORREÇÃO APLICADA NA CLÁUSULA order_by ---
    # Ordenamos primeiro pelo nome da Série e depois pelo nome do Aluno.
    # Isso garante que o filtro groupby('serie') no template funcione corretamente.
    matriculas = Matricula.query.join(Usuario, Matricula.aluno_id == Usuario.id)\
                                .join(Serie, Matricula.serie_id == Serie.id)\
                                .filter(
                                    Matricula.serie_id.in_(series_ids_int),
                                    Matricula.ano_letivo_id == ano_letivo_id
                                ).options(
                                    joinedload(Matricula.aluno), 
                                    joinedload(Matricula.serie)
                                ).order_by(Serie.nome, Usuario.nome).all()
    
    if not matriculas:
        flash('Nenhum aluno encontrado para os filtros selecionados.', 'info')
        return redirect(url_for('painel_relatorios'))

    # O resto do código continua o mesmo
    html_renderizado = render_template(
        'app/relatorios/alunos_por_serie.html', 
        matriculas=matriculas, 
        ano_letivo=ano_letivo, 
        data_geracao=datetime.now()
    )
    
    pdf = HTML(string=html_renderizado).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=relatorio_alunos_por_serie.pdf'
    return response

@app.route('/admin/relatorios/professores')
@login_required
@role_required('coordenador')
def relatorio_professores():
    professores = Usuario.query.filter_by(role='professor', escola_id=current_user.escola_id).order_by(Usuario.nome).all()
    html_renderizado = render_template('app/relatorios/lista_professores.html', professores=professores, data_geracao=datetime.now())
    pdf = HTML(string=html_renderizado).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=relatorio_professores.pdf'
    return response

@app.route('/admin/relatorios/resultado_simulado', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_resultado_simulado():
    avaliacao_id = request.form.get('avaliacao_id', type=int)
    if not avaliacao_id:
        flash('Você precisa selecionar um simulado.', 'warning')
        return redirect(url_for('painel_relatorios'))
    avaliacao = Avaliacao.query.options(joinedload(Avaliacao.resultados).joinedload(Resultado.aluno), joinedload(Avaliacao.criador)).filter_by(id=avaliacao_id, tipo='simulado', escola_id=current_user.escola_id).first_or_404()
    resultados_ordenados = sorted(avaliacao.resultados, key=lambda r: r.aluno.nome)
    html_renderizado = render_template('app/relatorios/resultado_simulado.html', avaliacao=avaliacao, resultados=resultados_ordenados, data_geracao=datetime.now())
    pdf = HTML(string=html_renderizado).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=relatorio_simulado_{avaliacao_id}.pdf'
    return response

@app.route('/admin/relatorios/boletim_aluno', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_boletim_aluno():
    serie_id = request.form.get('serie_id', type=int)
    ano_letivo_id = request.form.get('ano_letivo_id', type=int)
    if not serie_id or not ano_letivo_id:
        flash('Você precisa selecionar uma série e um ano letivo.', 'warning')
        return redirect(url_for('painel_relatorios'))

    ano_letivo = AnoLetivo.query.get(ano_letivo_id)
    serie_info = Serie.query.get(serie_id)
    
    matriculas = Matricula.query.filter_by(serie_id=serie_id, ano_letivo_id=ano_letivo_id).all()
    alunos_ids = [m.aluno_id for m in matriculas]
    alunos = Usuario.query.filter(Usuario.id.in_(alunos_ids)).order_by(Usuario.nome).all()

    if not alunos:
        flash('Nenhum aluno encontrado para os filtros selecionados.', 'info')
        return redirect(url_for('painel_relatorios'))

    dados_boletim_turma = []

    for aluno in alunos:
        notas_por_disciplina = {}
        
        # Otimiza a busca para já incluir o nome da avaliação
        resultados = Resultado.query.options(joinedload(Resultado.avaliacao)).filter(
            Resultado.aluno_id == aluno.id,
            Resultado.ano_letivo_id == ano_letivo_id,
            Avaliacao.tipo == 'prova'
        ).all()

        for resultado in resultados:
            if resultado.nota is not None and resultado.avaliacao.disciplina:
                disciplina_nome = resultado.avaliacao.disciplina.nome
                if disciplina_nome not in notas_por_disciplina:
                    notas_por_disciplina[disciplina_nome] = {'provas': [], 'media': 0.0}
                
                # CORREÇÃO PRINCIPAL: Armazenamos o nome da prova junto com a nota
                notas_por_disciplina[disciplina_nome]['provas'].append({
                    'nome': resultado.avaliacao.nome,
                    'nota': resultado.nota
                })
        
        for disciplina, dados in notas_por_disciplina.items():
            if dados['provas']:
                # Extrai apenas as notas para calcular a média
                soma_das_notas = sum(p['nota'] for p in dados['provas'])
                media = soma_das_notas / len(dados['provas'])
                dados['media'] = round(media, 2)
        
        dados_boletim_turma.append({'aluno': aluno, 'notas': notas_por_disciplina})

    html_renderizado = render_template(
        'app/relatorios/boletim_aluno.html',
        dados_boletim_turma=dados_boletim_turma,
        serie_info=serie_info,
        ano_letivo=ano_letivo,
        data_geracao=datetime.now()
    )
    
    pdf = HTML(string=html_renderizado).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=boletim_desempenho_turma.pdf'
    return response

@app.route('/responder_avaliacao/<int:avaliacao_id>', methods=['GET', 'POST'])
@login_required
@role_required('aluno')
def responder_avaliacao(avaliacao_id):
    # Otimiza a query para já carregar as questões junto com a avaliação
    avaliacao = Avaliacao.query.options(
        joinedload(Avaliacao.questoes)
    ).filter_by(id=avaliacao_id, escola_id=current_user.escola_id).first_or_404()

    # Busca por um resultado existente para este aluno e avaliação
    resultado_existente = Resultado.query.filter_by(
        aluno_id=current_user.id, 
        avaliacao_id=avaliacao.id
    ).first()

    # Se o resultado já foi finalizado ou está pendente de correção, bloqueia o acesso
    if resultado_existente and resultado_existente.status in ['Finalizado', 'Pendente']:
        flash('Você já enviou esta avaliação. Não é possível respondê-la novamente.', 'info')
        # Redireciona para a lista de modelos, que é a página inicial das avaliações para o aluno
        return redirect(url_for('listar_modelos_avaliacao'))

    if request.method == 'POST':
        # Envolve toda a lógica de submissão em um bloco try/except
        try:
            resultado = resultado_existente
            # Se não houver um resultado, cria um novo
            if not resultado:
                resultado = Resultado(
                    aluno_id=current_user.id, 
                    avaliacao_id=avaliacao.id, 
                    status='Iniciada', 
                    ano_letivo_id=avaliacao.ano_letivo_id
                )
                db.session.add(resultado)
            
            # Se o aluno está reenviando (ex: caiu a conexão), limpa as respostas antigas para evitar duplicatas
            elif resultado.respostas.count() > 0:
                Resposta.query.filter_by(resultado_id=resultado.id).delete()
                db.session.flush() # Aplica a exclusão antes de continuar

            total_pontos = 0
            possui_discursiva = False
            
            # Itera sobre todas as questões da avaliação para processar as respostas
            for questao in avaliacao.questoes:
                resposta_aluno_str = request.form.get(f'resposta_{questao.id}')

                # Cria o objeto da nova resposta
                nova_resposta = Resposta(
                    resultado=resultado, 
                    questao_id=questao.id, 
                    resposta_aluno=resposta_aluno_str
                )
                
                # Correção automática para questões não discursivas
                if questao.tipo != 'discursiva':
                    if resposta_aluno_str == questao.gabarito:
                        nova_resposta.status_correcao = 'correta'
                        nova_resposta.pontos = 1.0
                        total_pontos += 1.0
                    else:
                        nova_resposta.status_correcao = 'incorreta'
                        nova_resposta.pontos = 0.0
                else:
                    possui_discursiva = True
                    nova_resposta.status_correcao = 'nao_avaliada'
                    nova_resposta.pontos = 0.0 # Pontos de discursivas são atribuídos na correção
                
                db.session.add(nova_resposta)

            # Calcula a nota final e define o status
            total_questoes = len(avaliacao.questoes)
            resultado.nota = round((total_pontos / total_questoes) * 10, 2) if total_questoes > 0 else 0
            resultado.status = 'Pendente' if possui_discursiva else 'Finalizado'
            resultado.data_realizacao = datetime.utcnow()
            
            # Commita a transação inteira (resultado e todas as respostas)
            db.session.commit()

            # --- AUDITORIA: Registra a submissão da avaliação APÓS o commit bem-sucedido ---
            log_audit(
                'ASSESSMENT_SUBMITTED', 
                target_obj=avaliacao, 
                details={
                    'resultado_id': resultado.id,
                    'nota_parcial': resultado.nota,
                    'status_final': resultado.status
                }
            )

            flash('Avaliação enviada com sucesso!', 'success')
            return redirect(url_for('meus_resultados'))

        except Exception as e:
            # Em caso de qualquer erro, desfaz toda a operação
            db.session.rollback()
            print(f"ERRO AO ENVIAR AVALIAÇÃO: {e}")
            flash(f'Ocorreu um erro inesperado ao enviar sua avaliação. Por favor, tente novamente.', 'danger')
            return redirect(url_for('responder_avaliacao', avaliacao_id=avaliacao_id))

    # Lógica GET: Apenas renderiza a página da avaliação
    return render_template('app/responder_avaliacao.html', avaliacao=avaliacao, layout_simples=True)

# --- ROTAS DE API ---
@app.route('/api/conteudo_simulado/<int:serie_id>')
@login_required
def get_conteudo_simulado_por_serie(serie_id):
    """
    API para buscar todas as disciplinas e seus respectivos assuntos para uma série.
    """
    try:
        # Encontra todas as disciplinas que têm questões para a série informada.
        disciplinas_com_questoes = db.session.query(Disciplina).join(Questao).filter(
            Questao.serie_id == serie_id,
            Disciplina.escola_id == current_user.escola_id
        ).distinct().order_by(Disciplina.nome).all()

        if not disciplinas_com_questoes:
            return jsonify({'disciplinas': []})

        resultado_final = {'disciplinas': []}

        for disciplina in disciplinas_com_questoes:
            # CORREÇÃO: Busca os nomes distintos dos assuntos diretamente da tabela Questao
            assuntos_tuplas = db.session.query(Questao.assunto).filter(
                Questao.serie_id == serie_id,
                Questao.disciplina_id == disciplina.id
            ).distinct().order_by(Questao.assunto).all()
            
            # Converte a lista de tuplas em uma lista de dicionários que o frontend espera
            # Como 'assunto' é um texto e não tem um ID próprio, usamos o próprio nome como ID e nome.
            assuntos_da_disciplina = [{'id': nome_assunto[0], 'nome': nome_assunto[0]} for nome_assunto in assuntos_tuplas]
            
            disciplina_data = {
                'id': disciplina.id,
                'nome': disciplina.nome,
                'assuntos': assuntos_da_disciplina
            }
            resultado_final['disciplinas'].append(disciplina_data)
            
        return jsonify(resultado_final)

    except Exception as e:
        print(f"--- ERRO GRAVE NA API /api/conteudo_simulado ---")
        print(e)
        print("---------------------------------------------")
        return jsonify({'error': 'Ocorreu um erro interno no servidor'}), 500

@app.route('/api/assuntos')
@login_required
def get_assuntos_por_disciplina_e_serie():
    """
    API para buscar assuntos que POSSUEM questões com base na disciplina e na série.
    """
    try:
        disciplina_id = request.args.get('disciplina_id', type=int)
        serie_id = request.args.get('serie_id', type=int)

        if not disciplina_id or not serie_id:
            return jsonify({'error': 'Parâmetros disciplina_id e serie_id são obrigatórios'}), 400

        # CORREÇÃO: A query agora busca na coluna 'assunto' da tabela 'Questao'
        assuntos_tuplas = db.session.query(Questao.assunto).filter(
            Questao.disciplina_id == disciplina_id,
            Questao.serie_id == serie_id
        ).distinct().order_by(Questao.assunto).all()

        # O resultado é uma lista de tuplas, ex: [('Genética',), ('Citologia',)].
        # Precisamos converter para o formato que o JavaScript espera: [{'id': 'Genética', 'nome': 'Genética'}, ...]
        assuntos_list = [{'id': row[0], 'nome': row[0]} for row in assuntos_tuplas]
        
        return jsonify({'assuntos': assuntos_list})

    except Exception as e:
        print(f"--- ERRO GRAVE NA API /api/assuntos ---")
        print(e)
        print("---------------------------------------")
        return jsonify({'error': 'Ocorreu um erro interno ao buscar os assuntos.'}), 500

@app.route('/api/alunos_por_serie/<int:serie_id>')
@login_required
@role_required('coordenador')
def api_alunos_por_serie(serie_id):
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
    if not ano_letivo_ativo:
        return jsonify({'error': 'Ano letivo não encontrado'}), 404
    matriculas = Matricula.query.filter_by(serie_id=serie_id, ano_letivo_id=ano_letivo_ativo.id).all()
    alunos = []
    for matricula in matriculas:
        alunos.append({'id': matricula.aluno.id, 'nome': matricula.aluno.nome})
    alunos_ordenados = sorted(alunos, key=lambda x: x['nome'])
    return jsonify(alunos=alunos_ordenados)

# ===================================================================
# SEÇÃO FINAL: EXECUÇÃO
# ===================================================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)