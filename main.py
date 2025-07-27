# ===================================================================
# SEÇÃO 1: IMPORTS
# ===================================================================
import os
from jinja2 import ChoiceLoader, FileSystemLoader
from dotenv import load_dotenv
load_dotenv()
import resend
from PIL import Image
# ### ALTERAÇÃO: Adicionado Blueprint para organizar as rotas
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, make_response, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
# ### ALTERAÇÃO: Adicionado timedelta para definir a validade do token
from datetime import datetime, timedelta
import random
from weasyprint import HTML, CSS
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, UniqueConstraint, func, and_
import json
# ### ALTERAÇÃO: Adicionada a biblioteca JWT para gerar e verificar tokens da API
import jwt

# ===================================================================
# SEÇÃO 2: CONFIGURAÇÃO DO APLICATIVO E EXTENSÕES
# ===================================================================
app = Flask(__name__,
            # A pasta static_folder continua a mesma
            static_folder='site/static')

# ### CORREÇÃO APLICADA AQUI ###
# Esta nova configuração diz ao Flask para procurar templates em duas pastas:
# 1. Na pasta 'templates' (para os ficheiros da aplicação como 'app/base.html')
# 2. Na pasta 'site/templates' (para os ficheiros públicos como 'home_vendas.html')
app.jinja_loader = ChoiceLoader([
    FileSystemLoader('templates'),
    FileSystemLoader('site/templates'),
])


UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads/questoes')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Pasta para upload dos documentos (manuais, etc.)
UPLOAD_FOLDER_DOCS = os.path.join(app.static_folder, 'uploads/documentos')
ALLOWED_EXTENSIONS_DOCS = {'pdf', 'doc', 'docx'} # Defina as extensões permitidas
app.config['UPLOAD_FOLDER_DOCS'] = UPLOAD_FOLDER_DOCS

def allowed_doc_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_DOCS

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

# --- CONFIGURAÇÃO DOS PLANOS DE ASSINATURA ---
# Centraliza as regras de cada plano para fácil manutenção.
PLANS = {
    'essencial': {
        'questoes': 1000,
        'coordenador': 2,
        'professor': 50,
        'aluno': 500,
        'display_name': 'Plano Essencial'
    },
    'profissional': {
        'questoes': 2000,
        'coordenador': 4,
        'professor': 100,
        'aluno': 1000,
        'display_name': 'Plano Profissional'
    },
    'enterprise': {
        'questoes': float('inf'),  # 'inf' representa infinito (ilimitado)
        'coordenador': float('inf'),
        'professor': float('inf'),
        'aluno': float('inf'),
        'display_name': 'Plano Enterprise'
    }
}

# ===================================================================
# SEÇÃO 3: DECORATOR DE AUTORIZAÇÃO (WEB E API)
# ===================================================================

# Decorator para autenticação via Token JWT para a API
def token_required(f):
    """
    Verifica a validade de um token JWT enviado no cabeçalho da requisição.
    Se o token for válido, o usuário correspondente é passado para a rota.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # O token deve ser enviado no cabeçalho 'x-access-token'
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        
        if not token:
            return jsonify({'message': 'Token de acesso não encontrado!'}), 401
        
        try:
            # Decodifica o token usando a chave secreta da aplicação
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_api_user = Usuario.query.get(data['id'])
            if not current_api_user:
                 return jsonify({'message': 'Usuário do token não encontrado!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expirado!'}), 401
        except Exception as e:
            return jsonify({'message': 'Token inválido!', 'error': str(e)}), 401
        
        # Passa o objeto do usuário para a rota protegida
        return f(current_api_user, *args, **kwargs)
    return decorated

def role_required(*roles):
    """
    Decorator que verifica se o usuário tem um dos perfis necessários.
    Funciona tanto para a sessão web (current_user) quanto para a API (token).
    """
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Tenta identificar se o usuário veio de um token (primeiro argumento da rota)
            user_from_token = args[0] if args and isinstance(args[0], Usuario) else None

            if user_from_token:
                # Lógica para a API
                if user_from_token.role not in roles:
                    return jsonify({'error': 'Acesso não autorizado para este perfil.'}), 403
            # Lógica original para a aplicação web
            elif not current_user.is_authenticated or current_user.role not in roles:
                if request.accept_mimetypes.best_match(['application/json']):
                    return jsonify({'error': 'Acesso não autorizado para este perfil.'}), 403
                flash("Você não tem permissão para acessar esta página.", "danger")
                return redirect(url_for('main_routes.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_superadmin:
            flash("Você não tem permissão para acessar esta área.", "danger")
            return redirect(url_for('main_routes.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def check_plan_limit(resource_type):
    """
    Decorator que verifica se a escola atingiu o limite de um recurso.
    Atualmente focado na aplicação web.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # O superadmin não tem limites
            if current_user.is_superadmin:
                return f(*args, **kwargs)

            escola = current_user.escola
            if not escola or not escola.plano or escola.plano not in PLANS:
                flash('Plano da escola inválido ou não encontrado. Contate o suporte.', 'danger')
                return redirect(request.referrer or url_for('main_routes.dashboard'))

            plan_limits = PLANS[escola.plano]
            limit = plan_limits.get(resource_type)
            
            # Se o limite for infinito, permite a ação imediatamente
            if limit == float('inf'):
                return f(*args, **kwargs)

            # Conta a quantidade atual de recursos no banco de dados
            if resource_type in ['aluno', 'professor', 'coordenador']:
                current_count = Usuario.query.filter_by(escola_id=escola.id, role=resource_type).count()
            elif resource_type == 'questoes':
                current_count = db.session.query(Questao.id).join(Disciplina, Questao.disciplina_id == Disciplina.id).filter(Disciplina.escola_id == escola.id).count()
            else:
                return f(*args, **kwargs) # Tipo de recurso desconhecido, permite a passagem

            # Se o limite foi atingido, bloqueia e exibe uma mensagem
            if current_count >= limit:
                resource_name = resource_type.replace('_', ' ').capitalize() + 's'
                flash(f'Limite de {resource_name} ({int(limit)}) para o {plan_limits["display_name"]} foi atingido. Para adicionar mais, peça ao administrador para fazer um upgrade do plano.', 'warning')
                return redirect(request.referrer or url_for('main_routes.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ===================================================================
# SEÇÃO 4: MODELOS DO BANCO DE DADOS
# ===================================================================

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
    plano = db.Column(db.String(20), default='essencial', nullable=False)
    media_recuperacao = db.Column(db.Float, nullable=False, default=6.0, server_default='6.0')

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
    data_aceite_termos = db.Column(db.DateTime, nullable=True)
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

class Documento(db.Model):
    __tablename__ = 'documento'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    caminho_arquivo = db.Column(db.String(300), nullable=False)
    data_upload = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<Documento {self.titulo}>'

# ===================================================================
# SEÇÃO 5: API (V1)
# ===================================================================

# Cria um Blueprint para a API. Todas as rotas aqui começarão com /api/v1
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

@api_v1.route('/login', methods=['POST'])
def api_login():
    """Endpoint de login para a API, retorna um token JWT."""
    # Pega os dados JSON enviados na requisição
    auth = request.json
    if not auth or not auth.get('email') or not auth.get('password'):
        return make_response(jsonify({'error': 'Email ou senha não fornecidos'}), 401)

    # Busca o usuário no banco de dados
    user = Usuario.query.filter(func.lower(Usuario.email) == func.lower(auth.get('email'))).first()

    # Verifica se o usuário existe e se a senha está correta
    if not user or not check_password_hash(user.password, auth.get('password')):
        return make_response(jsonify({'error': 'Credenciais inválidas'}), 401)
    
    # Gera o token JWT com validade de 24 horas
    token = jwt.encode({
        'id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24) # 'exp' é um campo padrão para data de expiração
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({'token': token})

@api_v1.route('/perfil', methods=['GET'])
@token_required
def get_perfil(current_api_user):
    """Retorna os dados do perfil do usuário autenticado via token."""
    user_data = {
        'id': current_api_user.id,
        'nome': current_api_user.nome,
        'email': current_api_user.email,
        'role': current_api_user.role,
        'escola': current_api_user.escola.nome if current_api_user.escola else None
    }
    if current_api_user.role == 'aluno' and current_api_user.serie_atual:
        user_data['serie_atual'] = current_api_user.serie_atual.nome

    return jsonify(user_data)

@api_v1.route('/avaliacoes', methods=['GET'])
@token_required
@role_required('aluno') # Protege a rota para apenas alunos
def get_avaliacoes(current_api_user):
    """Retorna a lista de avaliações disponíveis para o aluno."""
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_api_user.escola_id, status='ativo').first()
    if not ano_letivo_ativo:
        return jsonify({'avaliacoes': [], 'message': 'Nenhum ano letivo ativo encontrado.'})

    modelos = []
    ids_concluidas = set()
    
    serie_aluno = current_api_user.serie_atual
    if not serie_aluno:
        return jsonify({'avaliacoes': [], 'message': 'Aluno não matriculado em nenhuma série.'})
    
    # Busca modelos e recuperações
    modelos_da_serie = ModeloAvaliacao.query.filter_by(serie_id=serie_aluno.id).order_by(ModeloAvaliacao.id.desc()).all()
    recuperacoes_designadas = current_api_user.avaliacoes_designadas
    
    avaliacoes_disponiveis = modelos_da_serie + recuperacoes_designadas
    
    # Verifica quais já foram concluídas
    resultados_finalizados_dinamicos = db.session.query(Avaliacao.modelo_id).join(Resultado).filter(
        Resultado.aluno_id == current_api_user.id, Resultado.status == 'Finalizado',
        Avaliacao.is_dinamica == True, Avaliacao.modelo_id.isnot(None)
    ).distinct().all()
    ids_concluidas.update([r.modelo_id for r in resultados_finalizados_dinamicos])

    resultados_finalizados_recuperacao = db.session.query(Resultado.avaliacao_id).filter(
        Resultado.aluno_id == current_api_user.id, Resultado.status == 'Finalizado',
        Resultado.avaliacao.has(tipo='recuperacao')
    ).distinct().all()
    ids_concluidas.update([r.avaliacao_id for r in resultados_finalizados_recuperacao])

    # Formata a saída em JSON
    output = []
    for avaliacao in avaliacoes_disponiveis:
        # Determina o tipo de disciplina para a exibição
        disciplina_nome = "Simulado"
        if isinstance(avaliacao, ModeloAvaliacao) and avaliacao.tipo == 'prova':
            # Para modelos de prova, a disciplina está nas regras de seleção
            if avaliacao.regras_selecao and avaliacao.regras_selecao.get('disciplinas'):
                disciplina_id = avaliacao.regras_selecao['disciplinas'][0]['id']
                disciplina = Disciplina.query.get(disciplina_id)
                if disciplina:
                    disciplina_nome = disciplina.nome
        elif isinstance(avaliacao, Avaliacao) and avaliacao.disciplina:
            # Para avaliações estáticas (recuperação), a disciplina está diretamente ligada
            disciplina_nome = avaliacao.disciplina.nome

        output.append({
            'id': avaliacao.id,
            'nome': avaliacao.nome,
            'tipo': avaliacao.tipo,
            'disciplina': disciplina_nome,
            'concluida': avaliacao.id in ids_concluidas,
            'is_modelo': isinstance(avaliacao, ModeloAvaliacao) # Flag para o app saber como chamar a rota
        })
        
    return jsonify({'avaliacoes': output})

# ===================================================================
# SEÇÃO 6: ROTAS DA APLICAÇÃO WEB (Refatorado para Blueprint)
# ===================================================================

# Cria um Blueprint para todas as rotas que renderizam templates HTML.
main_routes = Blueprint('main_routes', __name__)

def log_audit(action, target_obj=None, details=None):
    """
    Registra um evento de auditoria.
    """
    try:
        if request:
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        else:
            ip_address = None

        log_entry = AuditLog(
            action=action,
            details=details,
            ip_address=ip_address
        )

        if current_user and current_user.is_authenticated:
            log_entry.user_id = current_user.id
            log_entry.user_email = current_user.email
        elif request and request.form:
            log_entry.user_email = request.form.get('email', 'N/A')
        else:
            log_entry.user_email = 'Sistema'

        if target_obj and hasattr(target_obj, 'id'):
            log_entry.target_type = target_obj.__class__.__name__
            log_entry.target_id = target_obj.id

        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"ERRO CRÍTICO AO SALVAR LOG DE AUDITORIA: {e}")

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized_callback():
    if request.blueprint == 'api_v1':
        return jsonify({'error': 'Login necessário para acessar este recurso.'}), 401
    return redirect(url_for('main_routes.login'))

@app.before_request
def before_request_handler():
    if request.blueprint == 'api_v1':
        return
        
    if current_user.is_authenticated and current_user.precisa_trocar_senha:
        public_endpoints = [
            'main_routes.login', 'main_routes.logout', 'static', 
            'main_routes.pagina_inicial_vendas', 'main_routes.funcionalidades', 
            'main_routes.planos', 'main_routes.contato', 'main_routes.setup_inicial', 
            'main_routes.listar_documentos_publicos'
        ]
        if request.endpoint and request.endpoint not in public_endpoints and request.endpoint != 'main_routes.trocar_senha':
            return redirect(url_for('main_routes.trocar_senha'))

# --- Rotas Públicas e de SuperAdmin ---
@main_routes.route('/setup-inicial')
def setup_inicial():
    if Usuario.query.filter_by(is_superadmin=True).count() == 0:
        super_admin = Usuario(nome="Super Admin", email="manoelbd2012@gmail.com", password=generate_password_hash("Mf@871277", method='pbkdf2:sha256'), role="coordenador", escola_id=None, is_superadmin=True, precisa_trocar_senha=False)
        db.session.add(super_admin)
        db.session.commit()
        return "Super Admin criado com sucesso!"
    return "Super Admin já existe."

@main_routes.route('/')
def pagina_inicial_vendas():
    return render_template('home_vendas.html')

@main_routes.route('/funcionalidades')
def funcionalidades():
    return render_template('funcionalidades.html')

@main_routes.route('/planos')
def planos():
    return render_template('planos.html')

@main_routes.route('/contato', methods=['GET', 'POST'])
def contato():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email_remetente = request.form.get('email')
        mensagem = request.form.get('mensagem')
        if not nome or not email_remetente or not mensagem:
            flash('Por favor, preencha todos os campos obrigatórios.', 'danger')
            return render_template('contato.html')
        resend_api_key = os.environ.get('RESEND_API_KEY')
        if not resend_api_key:
            print("--- ERRO CRÍTICO: Chave da API do Resend (RESEND_API_KEY) não encontrada! ---")
            flash('Ocorreu um erro de configuração no servidor. Por favor, tente novamente mais tarde.', 'danger')
            return render_template('contato.html')
        try:
            resend.api_key = resend_api_key
            params = {
                # ### CORREÇÃO APLICADA AQUI ###
                # Alterado o remetente para um e-mail do seu domínio verificado.
                "from": "Contato OnlineTests <contato@onlinetests.com.br>", 
                "to": ["contato@onlinetests.com.br"],
                "subject": f"Nova Mensagem de Contato de {nome}",
                "html": f"""
                    <p>Você recebeu uma nova mensagem de contato através do site Online Tests.</p>
                    <p><strong>Nome:</strong> {nome}</p>
                    <p><strong>Email para resposta:</strong> {email_remetente}</p>
                    <hr>
                    <p><strong>Mensagem:</strong></p>
                    <p>{mensagem}</p>
                """,
                "reply_to": email_remetente
            }
            resend.Emails.send(params)
            flash('Sua mensagem foi enviada com sucesso! Entraremos em contato em breve.', 'success')
            return redirect(url_for('main_routes.contato'))
        except Exception as e:
            print(f"--- ERRO AO ENVIAR EMAIL COM RESEND: {e} ---")
            flash('Ocorreu um erro inesperado ao enviar sua mensagem. Por favor, tente novamente.', 'danger')
    return render_template('contato.html')

@main_routes.route('/documentos')
def listar_documentos_publicos():
    lista_documentos = Documento.query.filter_by(ativo=True).order_by(Documento.data_upload.desc()).all()
    return render_template('documentos.html', documentos=lista_documentos)

@main_routes.route('/superadmin/painel')
@login_required
@superadmin_required
def superadmin_painel():
    escolas_com_contagem = db.session.query(Escola, func.count(Usuario.id)).outerjoin(Usuario, and_(Escola.id == Usuario.escola_id, Usuario.role == 'aluno')).group_by(Escola.id).order_by(Escola.nome).all()
    return render_template('app/superadmin_painel.html', escolas_com_contagem=escolas_com_contagem)

@main_routes.route('/superadmin/editar-escola/<int:escola_id>', methods=['GET', 'POST'])
@login_required
@superadmin_required
def editar_escola(escola_id):
    escola = Escola.query.get_or_404(escola_id)
    coordenador = Usuario.query.filter_by(escola_id=escola.id, role='coordenador').first()
    if not coordenador:
        flash('Coordenador não encontrado para esta escola.', 'danger')
        return redirect(url_for('main_routes.superadmin_painel'))
    if request.method == 'POST':
        escola.nome = request.form.get('nome_escola')
        escola.cnpj = request.form.get('cnpj_escola')
        escola.plano = request.form.get('plano_escola')
        escola.media_recuperacao = request.form.get('media_recuperacao', type=float)
        coordenador.nome = request.form.get('nome_coordenador')
        coordenador.email = request.form.get('email_coordenador')
        nova_senha = request.form.get('senha_coordenador')
        if nova_senha:
            coordenador.password = generate_password_hash(nova_senha, method='pbkdf2:sha256')
            coordenador.precisa_trocar_senha = True
            flash('Senha do coordenador redefinida com sucesso!', 'info')
        try:
            db.session.commit()
            log_audit('SCHOOL_UPDATE', target_obj=escola, details={'plano_alterado_para': escola.plano})
            flash(f'Dados da escola "{escola.nome}" atualizados com sucesso!', 'success')
            return redirect(url_for('main_routes.superadmin_painel'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar os dados: {e}', 'danger')
    return render_template('app/editar_escola.html', escola=escola, coordenador=coordenador, plans=PLANS)

@main_routes.route('/superadmin/nova-escola', methods=['GET', 'POST'])
@login_required
@superadmin_required
def superadmin_nova_escola():
    if request.method == 'POST':
        # ... Lógica de criação de escola ...
        return redirect(url_for('main_routes.superadmin_painel'))
    return render_template('app/nova_escola.html', plans=PLANS)

@main_routes.route('/superadmin/escola/<int:escola_id>/toggle-status', methods=['POST'])
@login_required
@superadmin_required
def toggle_escola_status(escola_id):
    escola = Escola.query.get_or_404(escola_id)
    escola.status = 'bloqueado' if escola.status == 'ativo' else 'ativo'
    log_audit('SCHOOL_STATUS_CHANGED', target_obj=escola, details={'novo_status': escola.status})
    db.session.commit()
    flash(f"Status da escola '{escola.nome}' alterado para {escola.status}.", "info")
    return redirect(url_for('main_routes.superadmin_painel'))

@main_routes.route('/superadmin/gerenciar-documentos', methods=['GET', 'POST'])
@login_required
@superadmin_required
def superadmin_gerenciar_documentos():
    if request.method == 'POST':
        # ... Lógica de upload ...
        return redirect(url_for('main_routes.superadmin_gerenciar_documentos'))
    documentos = Documento.query.order_by(Documento.data_upload.desc()).all()
    return render_template('app/superadmin_documentos.html', documentos=documentos)

@main_routes.route('/superadmin/documento/<int:documento_id>/excluir', methods=['POST'])
@login_required
@superadmin_required
def superadmin_excluir_documento(documento_id):
    # ... Lógica de exclusão ...
    return redirect(url_for('main_routes.superadmin_gerenciar_documentos'))

# --- Rotas de Autenticação e Dashboard ---
@main_routes.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main_routes.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter(func.lower(Usuario.email) == func.lower(form.email.data)).first()
        if user and check_password_hash(user.password, form.password.data):
            if not user.is_superadmin and user.escola and user.escola.status == 'bloqueado':
                log_audit('LOGIN_BLOCKED_SCHOOL', target_obj=user, details={'escola_nome': user.escola.nome})
                flash('O acesso para esta escola está temporariamente bloqueado.', 'danger')
                return redirect(url_for('main_routes.login'))
            login_user(user)
            log_audit('LOGIN_SUCCESS', target_obj=user)
            if user.precisa_trocar_senha:
                flash('Este é o seu primeiro acesso. Por favor, crie uma nova senha.', 'info')
                return redirect(url_for('main_routes.trocar_senha'))
            return redirect(url_for('main_routes.dashboard'))
        else:
            log_audit('LOGIN_FAILURE')
            flash('Login inválido. Verifique seu e-mail e senha.', 'danger')
    return render_template('app/login.html', form=form)

@main_routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('main_routes.login'))

@main_routes.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_superadmin:
        return redirect(url_for('main_routes.superadmin_painel'))
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
    return render_template('app/dashboard.html', ano_letivo_ativo=ano_letivo_ativo)

@main_routes.route('/trocar-senha', methods=['GET', 'POST'])
@login_required
def trocar_senha():
    form = TrocarSenhaForm()
    if form.validate_on_submit():
        aceite_termos = request.form.get('aceite_termos')
        if not aceite_termos:
            flash('Você deve ler e aceitar os Termos de Uso para continuar.', 'danger')
            return render_template('app/trocar_senha.html', form=form)
        current_user.password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        current_user.precisa_trocar_senha = False
        current_user.data_aceite_termos = datetime.utcnow()
        db.session.commit()
        log_audit('TERMS_ACCEPTED', target_obj=current_user)
        log_audit('PASSWORD_CHANGED_FIRST_TIME', target_obj=current_user)
        flash('Sua senha foi atualizada com sucesso!', 'success')
        return redirect(url_for('main_routes.dashboard'))
    return render_template('app/trocar_senha.html', form=form)

# --- Rotas de Administração do Coordenador ---
@main_routes.route('/admin/gerenciar-ciclo', methods=['GET', 'POST'])
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
                return redirect(url_for('main_routes.gerenciar_ciclo'))
    ano_atual = datetime.now().year
    return render_template('app/gerenciar_ciclo.html', anos_letivos=anos_letivos, ano_atual=ano_atual)

@main_routes.route('/admin/gerenciar_usuarios', methods=['GET', 'POST'])
@login_required
@role_required('coordenador')
def gerenciar_usuarios():
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
    if not ano_letivo_ativo:
        flash('Nenhum ano letivo ativo encontrado. Crie um em "Gerenciar Ciclo".', 'warning')
        return redirect(url_for('main_routes.gerenciar_ciclo'))

    # ### CORREÇÃO APLICADA AQUI (LÓGICA DO POST) ###
    if request.method == 'POST':
        # Esta seção inteira estava faltando
        nome = request.form.get('nome')
        email = request.form.get('email')
        role = request.form.get('role')
        escola_id = current_user.escola_id

        # Verifica se o email já existe na escola
        email_existente = Usuario.query.filter(
            func.lower(Usuario.email) == func.lower(email),
            Usuario.escola_id == escola_id
        ).first()

        if email_existente:
            flash(f'O e-mail "{email}" já está cadastrado nesta escola.', 'danger')
            return redirect(url_for('main_routes.gerenciar_usuarios'))

        # Gera uma senha aleatória e segura para o primeiro acesso
        senha_provisoria = ''.join(random.choices('abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=8))
        
        try:
            novo_usuario = Usuario(
                nome=nome,
                email=email,
                password=generate_password_hash(senha_provisoria, method='pbkdf2:sha256'),
                role=role,
                escola_id=escola_id,
                precisa_trocar_senha=True # Força a troca de senha no primeiro login
            )
            db.session.add(novo_usuario)
            db.session.commit()
            log_audit('USER_CREATED', target_obj=novo_usuario, details={'role': role, 'creator': current_user.email})
            flash(f'{role.capitalize()} "{nome}" cadastrado com sucesso! A senha provisória é: {senha_provisoria}', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar usuário: {e}', 'danger')

        return redirect(url_for('main_routes.gerenciar_usuarios'))

    # Lógica do GET (permanece a mesma)
    series = Serie.query.filter_by(escola_id=current_user.escola_id).order_by(Serie.nome).all()
    disciplinas = Disciplina.query.filter_by(escola_id=current_user.escola_id).order_by(Disciplina.nome).all()
    # Usando joinedload para otimizar a consulta das séries dos alunos
    usuarios = Usuario.query.options(
        joinedload(Usuario.matriculas).joinedload(Matricula.serie)
    ).filter(
        Usuario.escola_id == current_user.escola_id,
        Usuario.is_superadmin == False
    ).order_by(Usuario.nome).all()
    
    return render_template('app/gerenciar_usuarios.html', series=series, disciplinas=disciplinas, usuarios=usuarios, ano_letivo_ativo=ano_letivo_ativo)

@main_routes.route('/admin/editar_usuario/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('coordenador')
def editar_usuario(user_id):
    usuario = Usuario.query.options(
        joinedload(Usuario.disciplinas_lecionadas), 
        joinedload(Usuario.series_lecionadas)
    ).filter_by(id=user_id, escola_id=current_user.escola_id).first_or_404()
    
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()

    if request.method == 'POST':
        # Lógica de edição (já parecia estar em desenvolvimento, mantida por enquanto)
        # ... Lógica de edição de usuário ...
        flash('Dados do usuário atualizados com sucesso!', 'success') # Exemplo de flash
        return redirect(url_for('main_routes.gerenciar_usuarios'))

    # ### CORREÇÃO APLICADA AQUI (LÓGICA DO GET) ###
    # Carrega os dados que estavam faltando para o template
    series = Serie.query.filter_by(escola_id=current_user.escola_id).order_by(Serie.nome).all()
    disciplinas = Disciplina.query.filter_by(escola_id=current_user.escola_id).order_by(Disciplina.nome).all()
    
    # Cria o JSON de séries para o JavaScript do template
    series_json = [{'id': s.id, 'nome': s.nome} for s in series]
    
    matricula_atual = None
    if ano_letivo_ativo and usuario.role == 'aluno':
        matricula_atual = Matricula.query.filter_by(aluno_id=user_id, ano_letivo_id=ano_letivo_ativo.id).first()

    # Passa todas as variáveis necessárias para o template
    return render_template(
        'app/editar_usuario.html', 
        usuario=usuario, 
        series=series, 
        disciplinas=disciplinas, 
        series_json=series_json,  # Esta era a variável que causava o erro
        matricula_atual=matricula_atual,
        ano_letivo_ativo=ano_letivo_ativo
    )

@main_routes.route('/admin/matricula/salvar', methods=['POST'])
@login_required
@role_required('coordenador')
def salvar_matricula():
    user_id = request.form.get('user_id', type=int)
    # ... Lógica de salvar matrícula ...
    return redirect(url_for('main_routes.editar_usuario', user_id=user_id))

@main_routes.route('/admin/gerenciar-academico', methods=['GET', 'POST'])
@login_required
@role_required('coordenador')
def gerenciar_academico():
    escola_id = current_user.escola_id
    if request.method == 'POST':
        action = request.form.get('action') # Identifica qual botão foi pressionado

        try:
            # --- AÇÃO 1: CADASTRAR NOVA SÉRIE ---
            if action == 'salvar_serie':
                nome_serie = request.form.get('nome_serie')
                if nome_serie:
                    existente = Serie.query.filter_by(nome=nome_serie, escola_id=escola_id).first()
                    if existente:
                        flash(f'A série "{nome_serie}" já existe.', 'warning')
                    else:
                        nova_serie = Serie(nome=nome_serie, escola_id=escola_id)
                        db.session.add(nova_serie)
                        db.session.commit()
                        flash(f'Série "{nome_serie}" cadastrada com sucesso!', 'success')
                else:
                    flash('O nome da série não pode ser vazio.', 'danger')

            # --- AÇÃO 2: CADASTRAR NOVA DISCIPLINA ---
            elif action == 'salvar_disciplina':
                nome_disciplina = request.form.get('nome_disciplina')
                if nome_disciplina:
                    existente = Disciplina.query.filter_by(nome=nome_disciplina, escola_id=escola_id).first()
                    if existente:
                        flash(f'A disciplina "{nome_disciplina}" já existe.', 'warning')
                    else:
                        nova_disciplina = Disciplina(nome=nome_disciplina, escola_id=escola_id)
                        db.session.add(nova_disciplina)
                        db.session.commit()
                        flash(f'Disciplina "{nome_disciplina}" cadastrada com sucesso!', 'success')
                else:
                    flash('O nome da disciplina não pode ser vazio.', 'danger')

            # --- AÇÃO 3: ASSOCIAR DISCIPLINAS A UMA SÉRIE ---
            elif action == 'salvar_associacao':
                serie_id = request.form.get('serie_id_associacao')
                disciplinas_ids = request.form.getlist('disciplinas_selecionadas')
                
                serie = Serie.query.get(serie_id)
                if serie:
                    disciplinas_selecionadas = Disciplina.query.filter(Disciplina.id.in_(disciplinas_ids)).all()
                    serie.disciplinas = disciplinas_selecionadas
                    db.session.commit()
                    flash(f'Disciplinas associadas à série "{serie.nome}" com sucesso!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro: {e}', 'danger')

        return redirect(url_for('main_routes.gerenciar_academico'))

    # Lógica GET (carregar dados para exibir na página)
    series = Serie.query.filter_by(escola_id=escola_id).options(joinedload(Serie.disciplinas)).order_by(Serie.nome).all()
    disciplinas = Disciplina.query.filter_by(escola_id=escola_id).order_by(Disciplina.nome).all()
    return render_template('app/gerenciar_academico.html', series=series, disciplinas=disciplinas)

# --- Rotas do Banco de Questões ---
@main_routes.route('/professor/criar_questao', methods=['GET', 'POST'])
@login_required
@role_required('professor', 'coordenador')
@check_plan_limit('questoes')
def criar_questao():
    if request.method == 'POST':
        # ... Lógica de criar questão ...
        return redirect(url_for('main_routes.banco_questoes'))
    # ... Lógica GET ...
    return render_template('app/criar_questao.html') # Simplificado

@main_routes.route('/professor/banco-questoes')
@login_required
@role_required('professor', 'coordenador')
def banco_questoes():
    questoes = Questao.query.options(joinedload(Questao.disciplina), joinedload(Questao.serie)).filter_by(criador_id=current_user.id).order_by(Questao.id.desc()).all()
    return render_template('app/banco_questoes.html', questoes=questoes)

@main_routes.route('/professor/editar-questao/<int:questao_id>', methods=['GET', 'POST'])
@login_required
@role_required('professor', 'coordenador')
def editar_questao(questao_id):
    # ... Lógica de permissão ...
    if request.method == 'POST':
        # ... Lógica de edição de questão ...
        return redirect(url_for('main_routes.banco_questoes'))
    # ... Lógica GET ...
    return render_template('app/editar_questao.html') # Simplificado

# --- Rotas de Avaliação ---
@main_routes.route('/criar-modelo-avaliacao', methods=['GET', 'POST'])
@login_required
@role_required('coordenador', 'professor')
def criar_modelo_avaliacao():
    escola_id = current_user.escola_id

    if request.method == 'POST':
        try:
            nome_modelo = request.form.get('nome_modelo')
            tipo_modelo = request.form.get('tipo_modelo')
            serie_id = request.form.get('serie_id', type=int)
            tempo_limite_str = request.form.get('tempo_limite')
            tempo_limite = int(tempo_limite_str) if tempo_limite_str and tempo_limite_str.isdigit() else None

            if not all([nome_modelo, tipo_modelo, serie_id]):
                flash('Nome do modelo, tipo e série são obrigatórios.', 'danger')
                return redirect(url_for('main_routes.criar_modelo_avaliacao'))

            regras_selecao = {'disciplinas': []}
            
            i = 0
            while f'disciplina_id_{i}' in request.form:
                disciplina_id = request.form.get(f'disciplina_id_{i}', type=int)
                if not disciplina_id:
                    i += 1
                    continue

                regra_disciplina = {
                    'id': disciplina_id,
                    'questoes_por_assunto': [],
                    'questoes_por_nivel': []
                }

                # Para provas, os assuntos são coletados de um campo multiselect
                if tipo_modelo == 'prova':
                    assuntos = request.form.getlist(f'regra_{i}_assunto_0')
                    for assunto in assuntos:
                        regra_disciplina['questoes_por_assunto'].append({'assunto': assunto, 'quantidade': 0}) # Quantidade por assunto não especificada neste modo

                # Coleta regras por nível de dificuldade
                niveis = ['facil', 'media', 'dificil']
                total_questoes_nivel = 0
                for nivel in niveis:
                    quantidade = request.form.get(f'regra_{i}_nivel_{nivel}_qtd', type=int)
                    if quantidade and quantidade > 0:
                        regra_disciplina['questoes_por_nivel'].append({'nivel': nivel, 'quantidade': quantidade})
                        total_questoes_nivel += quantidade
                
                # Só adiciona a regra se houver alguma questão a ser selecionada
                if total_questoes_nivel > 0 or (tipo_modelo == 'prova' and regra_disciplina['questoes_por_assunto']):
                     regras_selecao['disciplinas'].append(regra_disciplina)

                i += 1

            if not regras_selecao['disciplinas']:
                flash('Nenhuma regra de seleção de questões foi definida. Adicione a quantidade de questões para ao menos uma disciplina.', 'warning')
                # Precisamos recarregar os dados para o template em caso de falha na validação
                series = Serie.query.filter_by(escola_id=escola_id).order_by(Serie.nome).all()
                disciplinas = Disciplina.query.filter_by(escola_id=escola_id).order_by(Disciplina.nome).all()
                return render_template('app/criar_modelo_avaliacao.html', series=series, disciplinas=disciplinas)


            novo_modelo = ModeloAvaliacao(
                nome=nome_modelo, tipo=tipo_modelo, tempo_limite=tempo_limite,
                criador_id=current_user.id, serie_id=serie_id, escola_id=escola_id,
                regras_selecao=regras_selecao
            )
            db.session.add(novo_modelo)
            db.session.commit()
            
            log_audit('ASSESSMENT_MODEL_CREATED', target_obj=novo_modelo)
            flash(f'Modelo de avaliação "{nome_modelo}" criado com sucesso!', 'success')
            return redirect(url_for('main_routes.listar_modelos_avaliacao'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao criar o modelo: {e}', 'danger')
    
    # Lógica GET
    series = Serie.query.filter_by(escola_id=escola_id).order_by(Serie.nome).all()
    disciplinas = Disciplina.query.filter_by(escola_id=escola_id).order_by(Disciplina.nome).all()
    return render_template('app/criar_modelo_avaliacao.html', series=series, disciplinas=disciplinas)

@main_routes.route('/iniciar-avaliacao/<int:modelo_id>')
@login_required
@role_required('aluno')
def iniciar_avaliacao_dinamica(modelo_id):
    # 1. Carregar o modelo e o ano letivo ativo.
    modelo = ModeloAvaliacao.query.get_or_404(modelo_id)
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
    if not ano_letivo_ativo:
        flash('Não há um ano letivo ativo. Contate a coordenação da sua escola.', 'danger')
        return redirect(url_for('main_routes.listar_modelos_avaliacao'))

    # 2. Verificar se o aluno já tem um resultado para uma avaliação gerada por este modelo.
    #    Isso impede que o aluno gere múltiplas provas a partir do mesmo modelo.
    resultado_existente = Resultado.query.join(Avaliacao).filter(
        Avaliacao.modelo_id == modelo_id,
        Resultado.aluno_id == current_user.id
    ).first()

    if resultado_existente:
        flash('Você já iniciou esta avaliação. Continue de onde parou.', 'info')
        # Redireciona para a tentativa já existente.
        return redirect(url_for('main_routes.responder_avaliacao', avaliacao_id=resultado_existente.avaliacao_id))

    # Inicia a transação do banco de dados
    try:
        # 3. Lógica para selecionar as questões baseadas nas regras do modelo.
        questoes_selecionadas = []
        ids_questoes_usadas = set() # Usado para não selecionar a mesma questão duas vezes

        for regra in modelo.regras_selecao.get('disciplinas', []):
            disciplina_id = regra.get('id')
            
            # Monta a query base para esta disciplina
            query_base = Questao.query.filter(
                Questao.disciplina_id == disciplina_id,
                Questao.serie_id == modelo.serie_id,
                Questao.id.notin_(ids_questoes_usadas) # Evita duplicatas
            )

            # Seleção por NÍVEL
            for regra_nivel in regra.get('questoes_por_nivel', []):
                nivel = regra_nivel.get('nivel')
                quantidade = regra_nivel.get('quantidade', 0)
                if quantidade > 0:
                    questoes_por_nivel = query_base.filter(Questao.nivel == nivel).order_by(func.random()).limit(quantidade).all()
                    
                    if len(questoes_por_nivel) < quantidade:
                        flash(f'Atenção: Não foram encontradas questões suficientes de nível "{nivel}" para a disciplina. A prova foi gerada com menos questões.', 'warning')

                    for q in questoes_por_nivel:
                        if q.id not in ids_questoes_usadas:
                            questoes_selecionadas.append(q)
                            ids_questoes_usadas.add(q.id)
            
            # Seleção por ASSUNTO (para o tipo 'prova')
            ids_assuntos = [assunto_regra.get('assunto') for assunto_regra in regra.get('questoes_por_assunto', [])]
            if ids_assuntos:
                 # Esta parte pode ser expandida se a prova por assunto precisar de uma quantidade específica.
                 # Por enquanto, estamos priorizando a seleção por nível dentro dos assuntos definidos.
                 query_base = query_base.filter(Questao.assunto.in_(ids_assuntos))


        if not questoes_selecionadas:
            flash('Não foi possível gerar a avaliação pois não foram encontradas questões que atendam às regras definidas. Por favor, contate seu professor ou a coordenação.', 'danger')
            return redirect(url_for('main_routes.listar_modelos_avaliacao'))

        # 4. Criar a nova instância da Avaliação para este aluno.
        nova_avaliacao = Avaliacao(
            nome=modelo.nome,
            tipo=modelo.tipo,
            tempo_limite=modelo.tempo_limite,
            criador_id=modelo.criador_id,
            disciplina_id=modelo.regras_selecao['disciplinas'][0]['id'] if modelo.tipo == 'prova' else None,
            serie_id=modelo.serie_id,
            escola_id=current_user.escola_id,
            ano_letivo_id=ano_letivo_ativo.id,
            is_dinamica=True,
            modelo_id=modelo.id,
            questoes=questoes_selecionadas,
            alunos_designados=[current_user] # Designa a prova para o aluno atual
        )
        db.session.add(nova_avaliacao)
        
        # O flush é importante para que 'nova_avaliacao' receba um ID antes do commit,
        # permitindo que o 'Resultado' seja criado e vinculado a ela na mesma transação.
        db.session.flush()

        # 5. Criar o registro de resultado inicial.
        novo_resultado = Resultado(
            aluno_id=current_user.id,
            avaliacao_id=nova_avaliacao.id,
            ano_letivo_id=ano_letivo_ativo.id,
            status='Iniciada' # Status inicial da prova
        )
        db.session.add(novo_resultado)

        # 6. Salvar tudo no banco de dados e redirecionar.
        db.session.commit()
        log_audit('DYNAMIC_ASSESSMENT_STARTED', target_obj=nova_avaliacao, details={'modelo_id': modelo_id, 'aluno_id': current_user.id})
        flash(f'Avaliação "{modelo.nome}" iniciada com sucesso! Boa prova!', 'success')
        return redirect(url_for('main_routes.responder_avaliacao', avaliacao_id=nova_avaliacao.id))

    except Exception as e:
        db.session.rollback()
        print(f"ERRO AO INICIAR AVALIAÇÃO DINÂMICA: {e}") # Log para debug no servidor
        flash('Ocorreu um erro inesperado ao iniciar a avaliação. Tente novamente.', 'danger')
        return redirect(url_for('main_routes.listar_modelos_avaliacao'))

@main_routes.route('/modelos-avaliacoes')
@login_required
@role_required('aluno', 'professor', 'coordenador')
def listar_modelos_avaliacao():
    escola_id = current_user.escola_id
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=escola_id, status='ativo').first()

    if not ano_letivo_ativo:
        flash('Não há um ano letivo ativo. A funcionalidade de avaliações está limitada.', 'warning')
        return redirect(url_for('main_routes.dashboard'))

    # --- LÓGICA PARA PROFESSORES E COORDENADORES ---
    if current_user.role in ['coordenador', 'professor']:
        # Eles veem todos os modelos e avaliações de recuperação da escola
        
        # Carrega todos os modelos de avaliação da escola
        modelos = ModeloAvaliacao.query.filter_by(escola_id=escola_id).order_by(ModeloAvaliacao.nome).all()
        
        # Carrega todas as avaliações estáticas (recuperações) da escola no ano ativo
        recuperacoes = Avaliacao.query.filter(
            Avaliacao.escola_id == escola_id,
            Avaliacao.ano_letivo_id == ano_letivo_ativo.id,
            Avaliacao.is_dinamica == False
        ).order_by(Avaliacao.nome).all()

        return render_template('app/listar_avaliacoes_geradas.html', modelos=modelos, recuperacoes=recuperacoes)
    
    # --- LÓGICA PARA ALUNOS ---
    else: # Papel 'aluno'
        # Alunos veem uma lista filtrada para sua série, com o status de cada avaliação.
        serie_aluno = current_user.serie_atual
        if not serie_aluno:
            flash('Você não está matriculado em uma série no ano letivo ativo. Contate a secretaria.', 'warning')
            return render_template('app/listar_modelos_avaliacao.html', avaliacoes_disponiveis=[])

        # 1. Buscar todas as avaliações potenciais para o aluno
        # Modelos dinâmicos disponíveis para a série do aluno
        modelos_disponiveis = ModeloAvaliacao.query.filter_by(serie_id=serie_aluno.id).order_by(ModeloAvaliacao.nome).all()
        
        # Recuperações estáticas designadas especificamente para o aluno
        recuperacoes_designadas = Avaliacao.query.join(avaliacao_alunos_designados).filter(
            avaliacao_alunos_designados.c.usuario_id == current_user.id,
            Avaliacao.ano_letivo_id == ano_letivo_ativo.id
        ).order_by(Avaliacao.nome).all()

        # 2. Buscar todos os resultados do aluno para ver o status de cada avaliação
        resultados_do_aluno = Resultado.query.options(
            joinedload(Resultado.avaliacao) # Otimiza a query para já carregar a avaliação
        ).filter(
            Resultado.aluno_id == current_user.id,
            Resultado.ano_letivo_id == ano_letivo_ativo.id
        ).all()
        
        # 3. Mapear os resultados para fácil acesso
        # Mapa para avaliações dinâmicas (chave é o ID do modelo)
        mapa_resultados_modelo = {res.avaliacao.modelo_id: res for res in resultados_do_aluno if res.avaliacao and res.avaliacao.is_dinamica}
        # Mapa para avaliações estáticas (chave é o ID da avaliação)
        mapa_resultados_estatica = {res.avaliacao_id: res for res in resultados_do_aluno if res.avaliacao and not res.avaliacao.is_dinamica}

        # 4. Preparar a lista final para o template
        avaliacoes_para_aluno = []

        # Processa os modelos dinâmicos
        for modelo in modelos_disponiveis:
            resultado = mapa_resultados_modelo.get(modelo.id)
            status = resultado.status if resultado else 'Não Iniciada'
            avaliacoes_para_aluno.append({
                'tipo_obj': 'modelo',
                'objeto': modelo,
                'resultado': resultado,
                'status': status
            })

        # Processa as recuperações estáticas
        for recuperacao in recuperacoes_designadas:
            resultado = mapa_resultados_estatica.get(recuperacao.id)
            status = resultado.status if resultado else 'Não Iniciada'
            avaliacoes_para_aluno.append({
                'tipo_obj': 'recuperacao',
                'objeto': recuperacao,
                'resultado': resultado,
                'status': status
            })
            
        return render_template('app/listar_modelos_avaliacao.html', avaliacoes_disponiveis=avaliacoes_para_aluno)

@main_routes.route('/modelo-avaliacao/<int:modelo_id>/detalhes')
@login_required
@role_required('coordenador', 'professor')
def detalhes_modelo_avaliacao(modelo_id):
    # 1. Carrega o modelo de avaliação e verifica a permissão (se pertence à escola do usuário).
    modelo = ModeloAvaliacao.query.filter_by(id=modelo_id, escola_id=current_user.escola_id).first_or_404()

    # 2. Busca todos os resultados de avaliações que foram geradas a partir deste modelo.
    #    Usamos joinedload para carregar os dados do aluno e da avaliação de forma otimizada.
    resultados = Resultado.query.options(
        joinedload(Resultado.aluno),
        joinedload(Resultado.avaliacao)
    ).join(Avaliacao).filter(Avaliacao.modelo_id == modelo_id).order_by(
        Resultado.data_realizacao.desc()
    ).all()

    # 3. Calcula estatísticas básicas a partir dos resultados.
    stats = {
        'total_realizadas': 0,
        'media_geral': 0,
        'total_finalizadas': 0
    }
    soma_notas = 0
    
    if resultados:
        notas_validas = [r.nota for r in resultados if r.status == 'Finalizado' and r.nota is not None]
        stats['total_realizadas'] = len(resultados)
        stats['total_finalizadas'] = len(notas_validas)
        if stats['total_finalizadas'] > 0:
            soma_notas = sum(notas_validas)
            stats['media_geral'] = soma_notas / stats['total_finalizadas']

    # 4. Cria um mapa de disciplinas para facilitar a exibição das regras no template.
    #    Isso evita fazer consultas ao banco dentro do template.
    disciplinas_escola = Disciplina.query.filter_by(escola_id=current_user.escola_id).all()
    disciplinas_map = {d.id: d.nome for d in disciplinas_escola}

    # 5. Renderiza o template com todos os dados coletados e processados.
    return render_template(
        'app/detalhes_modelo_avaliacao.html', 
        modelo=modelo, 
        resultados=resultados, 
        stats=stats, 
        disciplinas_map=disciplinas_map
    )

@main_routes.route('/api/buscar-questoes')
@login_required
@role_required('professor', 'coordenador')
def buscar_questoes():
    """
    Endpoint de API para buscar questões no banco de dados com base em filtros.
    Retorna os resultados em formato JSON para serem usados com JavaScript.
    """
    try:
        disciplina_id = request.args.get('disciplina_id', type=int)
        assunto = request.args.get('assunto', '', type=str)
        nivel = request.args.get('nivel', '', type=str)
        
        if not disciplina_id:
            return jsonify({'error': 'O ID da disciplina é obrigatório.'}), 400

        # Constrói a query base
        query = Questao.query.join(Disciplina).filter(
            Disciplina.escola_id == current_user.escola_id,
            Questao.disciplina_id == disciplina_id
        )

        # Aplica filtros adicionais se eles foram fornecidos
        if assunto:
            query = query.filter(Questao.assunto.ilike(f'%{assunto}%'))
        if nivel:
            query = query.filter(Questao.nivel == nivel)

        questoes_encontradas = query.order_by(Questao.assunto).limit(50).all()

        # Formata os resultados para JSON
        resultados = []
        for q in questoes_encontradas:
            # Pega os 150 primeiros caracteres do texto para preview
            texto_preview = (q.texto[:150] + '...') if len(q.texto) > 150 else q.texto
            resultados.append({
                'id': q.id,
                'assunto': q.assunto,
                'nivel': q.nivel.capitalize(),
                'texto_preview': texto_preview
            })
            
        return jsonify(resultados)

    except Exception as e:
        print(f"ERRO AO BUSCAR QUESTÕES: {e}")
        return jsonify({'error': 'Ocorreu um erro interno no servidor.'}), 500

@main_routes.route('/criar-recuperacao', methods=['GET', 'POST'])
@login_required
@role_required('professor', 'coordenador')
def criar_recuperacao():
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
    if not ano_letivo_ativo:
        flash('Não é possível criar avaliações sem um ano letivo ativo.', 'warning')
        return redirect(url_for('main_routes.dashboard'))

    if request.method == 'POST':
        try:
            nome_avaliacao = request.form.get('nome_avaliacao')
            disciplina_id = request.form.get('disciplina_id', type=int)
            serie_id = request.form.get('serie_id', type=int)
            alunos_ids = request.form.getlist('alunos_ids', type=int)
            tempo_limite_str = request.form.get('tempo_limite')
            tempo_limite = int(tempo_limite_str) if tempo_limite_str and tempo_limite_str.isdigit() else None
            
            # ### ALTERAÇÃO PRINCIPAL AQUI ###
            # Captura a lista de IDs das questões selecionadas no formulário
            questoes_ids = request.form.getlist('questoes_ids', type=int)

            if not all([nome_avaliacao, disciplina_id, serie_id, alunos_ids]):
                flash('Nome, disciplina, série e ao menos um aluno são obrigatórios.', 'danger')
                return redirect(url_for('main_routes.criar_recuperacao'))
            
            # Valida e busca os objetos do banco de dados
            alunos_selecionados = Usuario.query.filter(Usuario.id.in_(alunos_ids)).all()
            # Garante que as questões selecionadas pertencem à escola do usuário
            questoes_selecionadas = Questao.query.join(Disciplina).filter(
                Questao.id.in_(questoes_ids),
                Disciplina.escola_id == current_user.escola_id
            ).all()

            # Garante que o número de questões encontradas é o mesmo que o de IDs enviados
            if len(questoes_selecionadas) != len(questoes_ids):
                flash('Uma ou mais questões selecionadas são inválidas. Tente novamente.', 'danger')
                return redirect(url_for('main_routes.criar_recuperacao'))

            nova_recuperacao = Avaliacao(
                nome=nome_avaliacao, 
                tipo='recuperacao', 
                tempo_limite=tempo_limite,
                disciplina_id=disciplina_id, 
                serie_id=serie_id, 
                criador_id=current_user.id, 
                escola_id=current_user.escola_id, 
                ano_letivo_id=ano_letivo_ativo.id, 
                is_dinamica=False
            )
            
            nova_recuperacao.questoes = questoes_selecionadas
            nova_recuperacao.alunos_designados = alunos_selecionados
            
            db.session.add(nova_recuperacao)
            db.session.commit()
            
            log_audit('RECOVERY_ASSESSMENT_CREATED', target_obj=nova_recuperacao, details={'num_questoes': len(questoes_ids)})
            flash(f'Prova de recuperação "{nome_avaliacao}" criada e designada com sucesso!', 'success')
            return redirect(url_for('main_routes.listar_modelos_avaliacao'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao criar a prova de recuperação: {e}', 'danger')
            return redirect(url_for('main_routes.criar_recuperacao'))

    # Lógica para o método GET
    series = Serie.query.filter_by(escola_id=current_user.escola_id).order_by(Serie.nome).all()
    disciplinas = Disciplina.query.filter_by(escola_id=current_user.escola_id).order_by(Disciplina.nome).all()
    
    return render_template('app/criar_recuperacao.html', series=series, disciplinas=disciplinas)

@main_routes.route('/avaliacoes')
@login_required
@role_required('coordenador', 'professor') # Adicionado para garantir a permissão correta
def listar_avaliacoes():
    """
    Lista as avaliações estáticas (ex: recuperações) criadas para a escola
    no ano letivo corrente. Visível apenas para Coordenadores e Professores.
    """
    escola_id = current_user.escola_id
    
    # Busca o ano letivo ativo para filtrar as avaliações relevantes
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=escola_id, status='ativo').first()

    if not ano_letivo_ativo:
        flash("Nenhum ano letivo ativo encontrado. Não é possível listar as avaliações.", "warning")
        return render_template('app/listar_avaliacoes.html', avaliacoes=[])

    # Busca no banco todas as avaliações que NÃO são dinâmicas (ou seja, foram criadas manualmente)
    # e que pertencem ao ano letivo ativo.
    # Usamos joinedload para otimizar a busca dos dados do criador, disciplina e série.
    avaliacoes_estaticas = Avaliacao.query.options(
        joinedload(Avaliacao.criador),
        joinedload(Avaliacao.disciplina),
        joinedload(Avaliacao.serie)
    ).filter(
        Avaliacao.escola_id == escola_id,
        Avaliacao.is_dinamica == False,
        Avaliacao.ano_letivo_id == ano_letivo_ativo.id
    ).order_by(Avaliacao.nome).all()

    return render_template('app/listar_avaliacoes.html', avaliacoes=avaliacoes_estaticas)

@main_routes.route('/avaliacao/<int:avaliacao_id>/detalhes')
@login_required
@role_required('coordenador', 'professor')
def detalhes_avaliacao(avaliacao_id):
    """
    Exibe os detalhes de uma avaliação estática (não dinâmica), incluindo
    os alunos designados, seus status e estatísticas gerais.
    """
    # 1. Carrega a avaliação, garantindo que ela é estática e pertence à escola do usuário.
    #    Usamos joinedload para carregar de forma otimizada as listas de questões,
    #    alunos designados e os resultados com os dados dos respectivos alunos.
    avaliacao = Avaliacao.query.options(
        joinedload(Avaliacao.questoes),
        joinedload(Avaliacao.alunos_designados),
        joinedload(Avaliacao.resultados).joinedload(Resultado.aluno),
        joinedload(Avaliacao.serie),
        joinedload(Avaliacao.disciplina)
    ).filter(
        Avaliacao.id == avaliacao_id,
        Avaliacao.escola_id == current_user.escola_id,
        Avaliacao.is_dinamica == False
    ).first_or_404()

    # 2. Processa os dados para facilitar a exibição no template.
    
    # Cria um dicionário mapeando o ID do aluno ao seu resultado, para busca rápida.
    resultados_map = {resultado.aluno_id: resultado for resultado in avaliacao.resultados}
    
    # Cria uma lista combinada de alunos com seus status (Iniciada, Finalizado, Não Iniciada).
    alunos_com_status = []
    for aluno in avaliacao.alunos_designados:
        resultado = resultados_map.get(aluno.id)
        alunos_com_status.append({
            'aluno': aluno,
            'resultado': resultado,
            'status': resultado.status if resultado else 'Não Iniciada'
        })

    # 3. Calcula estatísticas gerais da avaliação.
    stats = {
        'total_designados': len(avaliacao.alunos_designados),
        'total_realizadas': len(avaliacao.resultados),
        'total_finalizadas': 0,
        'media_geral': 0
    }
    
    # Filtra apenas os resultados finalizados que possuem nota para o cálculo da média.
    notas_validas = [r.nota for r in avaliacao.resultados if r.status == 'Finalizado' and r.nota is not None]
    if notas_validas:
        stats['total_finalizadas'] = len(notas_validas)
        stats['media_geral'] = sum(notas_validas) / len(notas_validas)

    # 4. Renderiza o template, passando todos os dados processados.
    return render_template(
        'app/detalhes_avaliacao.html',
        avaliacao=avaliacao,
        alunos_com_status=alunos_com_status,
        stats=stats
    )

@main_routes.route('/meus-resultados')
@login_required
@role_required('aluno')
def meus_resultados():
    """
    Exibe a lista de todos os resultados de avaliações (iniciadas ou finalizadas)
    para o aluno logado no ano letivo corrente.
    """
    # Busca o ano letivo ativo para a escola do aluno.
    ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()

    if not ano_letivo_ativo:
        flash("Nenhum ano letivo ativo encontrado. Não é possível exibir seus resultados.", "warning")
        return render_template('app/meus_resultados.html', resultados=[])

    # Busca todos os resultados do aluno no ano letivo ativo.
    # Usamos joinedload para carregar de forma otimizada os dados da avaliação
    # e da disciplina associada a cada avaliação, evitando múltiplas queries.
    resultados_aluno = Resultado.query.options(
        joinedload(Resultado.avaliacao).joinedload(Avaliacao.disciplina),
        joinedload(Resultado.avaliacao).joinedload(Avaliacao.serie)
    ).filter(
        Resultado.aluno_id == current_user.id,
        Resultado.ano_letivo_id == ano_letivo_ativo.id
    ).order_by(Resultado.data_realizacao.desc()).all()

    # Renderiza o template, passando a lista de resultados encontrados.
    return render_template('app/meus_resultados.html', resultados=resultados_aluno)

@main_routes.route('/resultado/<int:resultado_id>')
@login_required
@role_required('aluno')
def ver_resultado_detalhado(resultado_id):
    """
    Exibe a página de detalhes de um resultado de avaliação específico para o aluno,
    mostrando cada questão, a resposta do aluno, o gabarito e o feedback (se houver).
    """
    # 1. Carrega o resultado e todos os dados relacionados de forma otimizada.
    #    - Garante que o resultado pertence ao aluno logado (verificação de segurança).
    #    - Usa joinedload para carregar a avaliação, suas questões, e as respostas do aluno
    #      com suas respectivas questões, tudo em uma consulta eficiente.
    resultado = Resultado.query.options(
        joinedload(Resultado.avaliacao).subqueryload(Avaliacao.questoes),
        joinedload(Resultado.respostas).joinedload(Resposta.questao)
    ).filter(
        Resultado.id == resultado_id,
        Resultado.aluno_id == current_user.id
    ).first_or_404()

    # 2. Cria um dicionário para mapear o ID de cada questão à resposta dada pelo aluno.
    #    Isso simplifica muito a lógica no template, evitando buscas dentro de loops.
    respostas_map = {resposta.questao_id: resposta for resposta in resultado.respostas}

    # 3. Renderiza o template, passando o resultado completo e o mapa de respostas.
    #    O template irá iterar sobre `resultado.avaliacao.questoes` e, para cada questão,
    #    usará o `respostas_map` para encontrar a resposta do aluno correspondente.
    return render_template(
        'app/ver_resultado.html', 
        resultado=resultado, 
        respostas_map=respostas_map
    )

@main_routes.route('/correcao/avaliacao/<int:avaliacao_id>')
@login_required
@role_required('professor', 'coordenador')
def correcao_lista_alunos(avaliacao_id):
    """
    Lista todos os resultados (tentativas) dos alunos para uma avaliação específica,
    permitindo que o professor/coordenador selecione uma para corrigir.
    Funciona tanto para avaliações dinâmicas quanto estáticas.
    """
    # 1. Carrega a avaliação e todos os seus resultados associados.
    #    - Garante que a avaliação pertence à escola do usuário.
    #    - Usa joinedload para carregar os dados do aluno de cada resultado e
    #      a série da avaliação de forma otimizada.
    avaliacao = Avaliacao.query.options(
        joinedload(Avaliacao.resultados).joinedload(Resultado.aluno),
        joinedload(Avaliacao.serie)
    ).filter(
        Avaliacao.id == avaliacao_id,
        Avaliacao.escola_id == current_user.escola_id
    ).first_or_404()

    # 2. Ordena os resultados pelo nome do aluno para uma exibição consistente.
    #    A ordenação é feita em Python após a consulta, pois ordenar por um
    #    campo de uma tabela juntada pode ser complexo e variar entre bancos de dados.
    resultados_ordenados = sorted(avaliacao.resultados, key=lambda r: r.aluno.nome)

    # 3. Renderiza o template, passando a avaliação e a lista ordenada de resultados.
    return render_template(
        'app/correcao_lista.html', 
        avaliacao=avaliacao, 
        resultados=resultados_ordenados
    )

@main_routes.route('/correcao/resultado/<int:resultado_id>', methods=['GET', 'POST'])
@login_required
@role_required('professor', 'coordenador')
def corrigir_respostas(resultado_id):
    """
    Exibe a interface de correção para um resultado específico (GET) e
    processa o envio da correção (POST).
    """
    # 1. Carrega o resultado e todos os dados relacionados de forma otimizada.
    #    - A verificação de permissão é feita garantindo que a avaliação pertence à escola do usuário.
    resultado = Resultado.query.options(
        joinedload(Resultado.aluno),
        joinedload(Resultado.avaliacao).subqueryload(Avaliacao.questoes),
        joinedload(Resultado.respostas).joinedload(Resposta.questao)
    ).join(Avaliacao).filter(
        Resultado.id == resultado_id,
        Avaliacao.escola_id == current_user.escola_id
    ).first_or_404()

    # --- LÓGICA DO POST: Salvar a correção ---
    if request.method == 'POST':
        try:
            total_nota = 0
            # Itera sobre as respostas dadas pelo aluno para atualizar cada uma.
            for resposta in resultado.respostas:
                questao_id = resposta.questao_id
                
                # Pega os pontos e o feedback do formulário
                pontos = request.form.get(f'pontos_{questao_id}', type=float, default=0.0)
                feedback = request.form.get(f'feedback_{questao_id}', '')

                # Atualiza o objeto Resposta
                resposta.pontos = pontos
                resposta.feedback_professor = feedback
                resposta.status_correcao = 'avaliada'
                
                total_nota += pontos

            # Atualiza o objeto Resultado principal com a nota e o novo status
            resultado.nota = total_nota
            resultado.status = 'Finalizado'

            db.session.commit()
            
            log_audit('ASSESSMENT_GRADED', target_obj=resultado, details={'final_score': total_nota, 'grader_id': current_user.id})
            flash(f'Avaliação de {resultado.aluno.nome} corrigida e finalizada com sucesso!', 'success')

            # Redireciona para a página de detalhes apropriada
            if resultado.avaliacao.is_dinamica and resultado.avaliacao.modelo_id:
                return redirect(url_for('main_routes.detalhes_modelo_avaliacao', modelo_id=resultado.avaliacao.modelo_id))
            else:
                return redirect(url_for('main_routes.detalhes_avaliacao', avaliacao_id=resultado.avaliacao.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Ocorreu um erro ao salvar a correção: {e}", "danger")

    # --- LÓGICA DO GET: Exibir a página para correção ---
    # Cria o mapa de respostas para facilitar a vida do template
    respostas_map = {resposta.questao_id: resposta for resposta in resultado.respostas}
    
    return render_template(
        'app/correcao_respostas.html',
        resultado=resultado,
        respostas_map=respostas_map
    )

@main_routes.route('/admin/relatorios')
@login_required
@role_required('coordenador')
def painel_relatorios():
    """
    Carrega todos os dados necessários (listas de séries, disciplinas, alunos, etc.)
    para popular os formulários no painel de geração de relatórios do coordenador.
    """
    escola_id = current_user.escola_id

    # Carrega as listas de entidades da escola para usar nos menus de seleção (dropdowns)
    
    # Lista de anos letivos para filtro de período
    anos_letivos = AnoLetivo.query.filter_by(escola_id=escola_id).order_by(AnoLetivo.ano.desc()).all()
    
    # Lista de séries para relatórios por turma
    series = Serie.query.filter_by(escola_id=escola_id).order_by(Serie.nome).all()
    
    # Lista de disciplinas para relatórios de desempenho por matéria
    disciplinas = Disciplina.query.filter_by(escola_id=escola_id).order_by(Disciplina.nome).all()
    
    # Lista de alunos para relatórios individuais, como boletins
    alunos = Usuario.query.filter_by(escola_id=escola_id, role='aluno').order_by(Usuario.nome).all()
    
    # Lista de modelos de avaliação para relatórios de simulados e provas
    modelos_avaliacao = ModeloAvaliacao.query.filter_by(escola_id=escola_id).order_by(ModeloAvaliacao.nome).all()

    # Renderiza o template, passando todas as listas de dados
    return render_template(
        'app/painel_relatorios.html',
        anos_letivos=anos_letivos,
        series=series,
        disciplinas=disciplinas,
        alunos=alunos,
        modelos_avaliacao=modelos_avaliacao
    )

@main_routes.route('/admin/auditoria')
@login_required
@role_required('coordenador')
def painel_auditoria():
    """
    Exibe o painel de auditoria com logs de eventos do sistema,
    com funcionalidades de busca, filtro e paginação.
    """
    escola_id = current_user.escola_id
    
    # --- Paginação e Filtros ---
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    action_filter = request.args.get('action_filter', '')

    # --- Query Base ---
    # Começamos buscando os logs e juntando com a tabela de usuários para poder filtrar pela escola.
    # Ordenamos pelos mais recentes primeiro.
    query = AuditLog.query.options(joinedload(AuditLog.user)).join(
        Usuario, AuditLog.user_id == Usuario.id
    ).filter(
        Usuario.escola_id == escola_id
    ).order_by(AuditLog.timestamp.desc())

    # --- Aplicando Filtros ---
    if search_query:
        # Permite buscar por email do usuário, IP ou detalhes da ação
        query = query.filter(or_(
            AuditLog.user_email.ilike(f'%{search_query}%'),
            AuditLog.ip_address.ilike(f'%{search_query}%'),
            AuditLog.details.cast(db.String).ilike(f'%{search_query}%') # Busca no JSON de detalhes
        ))
    
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    # --- Paginação ---
    per_page = 25  # Define quantos logs por página
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items

    # --- Dados para os Filtros do Template ---
    # Busca todos os tipos de ação únicos que já ocorreram na escola para popular o menu de filtro.
    # Isso torna o filtro mais inteligente, mostrando apenas ações relevantes.
    try:
        distinct_actions_query = db.session.query(AuditLog.action).join(
            Usuario, AuditLog.user_id == Usuario.id
        ).filter(
            Usuario.escola_id == escola_id
        ).distinct().order_by(AuditLog.action)
        
        unique_actions = [item[0] for item in distinct_actions_query.all()]
    except Exception as e:
        print(f"Erro ao buscar ações distintas para o filtro de auditoria: {e}")
        unique_actions = []


    return render_template(
        'app/painel_auditoria.html',
        logs=logs,
        pagination=pagination,
        unique_actions=unique_actions,
        # Devolve os filtros atuais para o template para manter o estado dos formulários
        search_query=search_query,
        action_filter=action_filter
    )

@main_routes.route('/admin/relatorios/desempenho_por_assunto', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_desempenho_por_assunto():
    """
    Gera um relatório em PDF mostrando o desempenho dos alunos por assunto
    dentro de uma disciplina e série específicas.
    """
    try:
        # 1. Obter os filtros do formulário
        serie_id = request.form.get('serie_id', type=int)
        disciplina_id = request.form.get('disciplina_id', type=int)
        ano_letivo_id = request.form.get('ano_letivo_id', type=int)

        if not all([serie_id, disciplina_id, ano_letivo_id]):
            flash('Série, disciplina e ano letivo são obrigatórios para gerar este relatório.', 'danger')
            return redirect(url_for('main_routes.painel_relatorios'))

        # 2. Buscar os nomes para o cabeçalho do relatório
        serie = Serie.query.get(serie_id)
        disciplina = Disciplina.query.get(disciplina_id)
        ano_letivo = AnoLetivo.query.get(ano_letivo_id)

        # 3. Consulta agregada para calcular o desempenho por assunto
        #    Esta é a parte mais importante: o banco de dados faz todo o trabalho pesado.
        desempenho_por_assunto = db.session.query(
            Questao.assunto,
            func.count(Resposta.id).label('total_respostas'),
            # Usamos case para contar condicionalmente os acertos (resposta == gabarito)
            func.sum(case((Resposta.resposta_aluno == Questao.gabarito, 1), else_=0)).label('total_acertos')
        ).join(Questao, Resposta.questao_id == Questao.id
        ).join(Resultado, Resposta.resultado_id == Resultado.id
        ).join(Avaliacao, Resultado.avaliacao_id == Avaliacao.id
        ).filter(
            Avaliacao.serie_id == serie_id,
            Questao.disciplina_id == disciplina_id, # Filtra pela disciplina na questão
            Resultado.ano_letivo_id == ano_letivo_id,
            Avaliacao.escola_id == current_user.escola_id
        ).group_by(Questao.assunto
        ).order_by(Questao.assunto).all()

        if not desempenho_por_assunto:
            flash('Nenhum dado encontrado para os filtros selecionados. Não é possível gerar o relatório.', 'warning')
            return redirect(url_for('main_routes.painel_relatorios'))

        # 4. Renderizar um template HTML que servirá de base para o PDF
        #    (Este template é apenas para a geração do PDF, não para ser exibido diretamente)
        html_renderizado = render_template(
            'app/reports/desempenho_assunto_pdf.html',
            serie=serie,
            disciplina=disciplina,
            ano_letivo=ano_letivo,
            desempenho_data=desempenho_por_assunto,
            data_geracao=datetime.now()
        )

        # 5. Usar WeasyPrint para converter o HTML em PDF
        pdf = HTML(string=html_renderizado).write_pdf()

        # 6. Criar e retornar a resposta com o PDF
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=desempenho_{serie.nome}_{disciplina.nome}.pdf'
        
        log_audit('REPORT_GENERATED', details={'report_type': 'desempenho_por_assunto', 'filters': f'Série ID: {serie_id}, Disciplina ID: {disciplina_id}'})
        return response

    except Exception as e:
        print(f"ERRO ao gerar relatório de desempenho por assunto: {e}")
        flash("Ocorreu um erro inesperado ao gerar o relatório. Tente novamente.", "danger")
        return redirect(url_for('main_routes.painel_relatorios'))

@main_routes.route('/admin/relatorios/desempenho_por_nivel', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_desempenho_por_nivel():
    """
    Gera um relatório em PDF mostrando o desempenho dos alunos por nível de dificuldade
    (fácil, médio, difícil) para uma disciplina e série específicas.
    """
    try:
        # 1. Obter os filtros do formulário
        serie_id = request.form.get('serie_id', type=int)
        disciplina_id = request.form.get('disciplina_id', type=int)
        ano_letivo_id = request.form.get('ano_letivo_id', type=int)

        if not all([serie_id, disciplina_id, ano_letivo_id]):
            flash('Série, disciplina e ano letivo são obrigatórios para gerar este relatório.', 'danger')
            return redirect(url_for('main_routes.painel_relatorios'))

        # 2. Buscar os nomes para o cabeçalho do relatório
        serie = Serie.query.get(serie_id)
        disciplina = Disciplina.query.get(disciplina_id)
        ano_letivo = AnoLetivo.query.get(ano_letivo_id)

        # 3. Consulta agregada para calcular o desempenho por NÍVEL
        desempenho_por_nivel = db.session.query(
            Questao.nivel,
            func.count(Resposta.id).label('total_respostas'),
            func.sum(case((Resposta.resposta_aluno == Questao.gabarito, 1), else_=0)).label('total_acertos')
        ).join(Questao, Resposta.questao_id == Questao.id
        ).join(Resultado, Resposta.resultado_id == Resultado.id
        ).join(Avaliacao, Resultado.avaliacao_id == Avaliacao.id
        ).filter(
            Avaliacao.serie_id == serie_id,
            Questao.disciplina_id == disciplina_id,
            Resultado.ano_letivo_id == ano_letivo_id,
            Avaliacao.escola_id == current_user.escola_id
        ).group_by(Questao.nivel).all() # <<< A MUDANÇA PRINCIPAL ESTÁ AQUI

        if not desempenho_por_nivel:
            flash('Nenhum dado encontrado para os filtros selecionados. Não é possível gerar o relatório.', 'warning')
            return redirect(url_for('main_routes.painel_relatorios'))
            
        # Opcional: Ordenar os resultados para garantir a ordem 'facil', 'media', 'dificil'
        ordem_niveis = {'facil': 0, 'media': 1, 'dificil': 2}
        desempenho_ordenado = sorted(desempenho_por_nivel, key=lambda x: ordem_niveis.get(x.nivel, 99))

        # 4. Renderizar um template HTML específico para este relatório
        html_renderizado = render_template(
            'app/reports/desempenho_nivel_pdf.html',
            serie=serie,
            disciplina=disciplina,
            ano_letivo=ano_letivo,
            desempenho_data=desempenho_ordenado,
            data_geracao=datetime.now()
        )

        # 5. Usar WeasyPrint para converter o HTML em PDF
        pdf = HTML(string=html_renderizado).write_pdf()

        # 6. Criar e retornar a resposta com o PDF
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=desempenho_por_nivel_{serie.nome}_{disciplina.nome}.pdf'
        
        log_audit('REPORT_GENERATED', details={'report_type': 'desempenho_por_nivel', 'filters': f'Série ID: {serie_id}, Disciplina ID: {disciplina_id}'})
        return response

    except Exception as e:
        print(f"ERRO ao gerar relatório de desempenho por nível: {e}")
        flash("Ocorreu um erro inesperado ao gerar o relatório. Tente novamente.", "danger")
        return redirect(url_for('main_routes.painel_relatorios'))

@main_routes.route('/admin/relatorios/analise_de_itens', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_analise_de_itens():
    """
    Gera um relatório PDF de Análise de Itens para um Modelo de Avaliação,
    mostrando o índice de dificuldade e a análise de distratores para cada questão.
    """
    try:
        # 1. Obter os filtros do formulário
        modelo_id = request.form.get('modelo_id', type=int)
        ano_letivo_id = request.form.get('ano_letivo_id', type=int)

        if not all([modelo_id, ano_letivo_id]):
            flash('Modelo de avaliação e ano letivo são obrigatórios para gerar este relatório.', 'danger')
            return redirect(url_for('main_routes.painel_relatorios'))

        # 2. Buscar informações para o cabeçalho
        modelo = ModeloAvaliacao.query.get(modelo_id)
        ano_letivo = AnoLetivo.query.get(ano_letivo_id)
        if not modelo or not ano_letivo or modelo.escola_id != current_user.escola_id:
            abort(404) # Garante que o coordenador não acesse dados de outra escola

        # 3. Buscar todos os dados de respostas relevantes de uma só vez
        # Encontra todos os resultados de avaliações geradas pelo modelo no ano letivo
        resultados = Resultado.query.join(Avaliacao).filter(
            Avaliacao.modelo_id == modelo_id,
            Resultado.ano_letivo_id == ano_letivo_id
        ).all()
        
        if not resultados:
            flash('Nenhuma avaliação foi realizada para este modelo nos filtros selecionados.', 'warning')
            return redirect(url_for('main_routes.painel_relatorios'))

        resultado_ids = [r.id for r in resultados]
        
        # Pega todas as respostas e as questões associadas de uma vez
        respostas = Resposta.query.options(joinedload(Resposta.questao)).filter(
            Resposta.resultado_id.in_(resultado_ids)
        ).all()

        # 4. Processar os dados em Python para fazer a análise
        analise_itens = {}
        # Primeiro, inicializamos a estrutura de dados para cada questão
        for resp in respostas:
            q_id = resp.questao_id
            if q_id not in analise_itens:
                analise_itens[q_id] = {
                    'questao': resp.questao,
                    'total_respostas': 0,
                    'total_acertos': 0,
                    'distratores': {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'NULA': 0}
                }
        
        # Agora, populamos a análise com os dados das respostas
        for resp in respostas:
            q_id = resp.questao_id
            stats = analise_itens[q_id]
            stats['total_respostas'] += 1
            
            # Contabiliza acertos
            if resp.resposta_aluno == stats['questao'].gabarito:
                stats['total_acertos'] += 1
            
            # Contabiliza distratores
            if resp.resposta_aluno in stats['distratores']:
                stats['distratores'][resp.resposta_aluno] += 1
            else:
                stats['distratores']['NULA'] += 1 # Respostas em branco ou inválidas

        # 5. Renderizar o template HTML para o PDF
        html_renderizado = render_template(
            'app/reports/analise_itens_pdf.html',
            modelo=modelo,
            ano_letivo=ano_letivo,
            analise_data=analise_itens.values(), # Passa a lista de análises
            data_geracao=datetime.now()
        )

        # 6. Gerar o PDF e retornar a resposta
        pdf = HTML(string=html_renderizado).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=analise_de_itens_{modelo.nome}.pdf'
        
        log_audit('REPORT_GENERATED', details={'report_type': 'analise_de_itens', 'filters': f'Modelo ID: {modelo_id}'})
        return response

    except Exception as e:
        print(f"ERRO ao gerar relatório de análise de itens: {e}")
        flash("Ocorreu um erro inesperado ao gerar o relatório. Tente novamente.", "danger")
        return redirect(url_for('main_routes.painel_relatorios'))

@main_routes.route('/admin/relatorios/saude_banco_questoes', methods=['GET'])
@login_required
@role_required('coordenador')
def relatorio_saude_banco_questoes():
    """
    Gera um relatório PDF com estatísticas sobre a "saúde" do banco de questões
    da escola, mostrando a distribuição por disciplina, série e nível.
    """
    try:
        escola_id = current_user.escola_id

        # 1. Contagem total de questões na escola
        total_questoes = db.session.query(func.count(Questao.id)).join(
            Disciplina, Questao.disciplina_id == Disciplina.id
        ).filter(Disciplina.escola_id == escola_id).scalar() or 0

        # 2. Contagem de questões por Disciplina
        stats_por_disciplina = db.session.query(
            Disciplina.nome, func.count(Questao.id)
        ).outerjoin(Questao, Disciplina.id == Questao.disciplina_id
        ).filter(Disciplina.escola_id == escola_id
        ).group_by(Disciplina.id).order_by(Disciplina.nome).all()

        # 3. Contagem de questões por Série
        stats_por_serie = db.session.query(
            Serie.nome, func.count(Questao.id)
        ).outerjoin(Questao, Serie.id == Questao.serie_id
        ).filter(Serie.escola_id == escola_id
        ).group_by(Serie.id).order_by(Serie.nome).all()

        # 4. Contagem de questões por Nível de Dificuldade
        stats_por_nivel = db.session.query(
            Questao.nivel, func.count(Questao.id)
        ).join(Disciplina, Questao.disciplina_id == Disciplina.id
        ).filter(Disciplina.escola_id == escola_id
        ).group_by(Questao.nivel).all()

        # 5. Renderizar o template HTML para o PDF
        html_renderizado = render_template(
            'app/reports/saude_banco_questoes_pdf.html',
            total_questoes=total_questoes,
            stats_por_disciplina=stats_por_disciplina,
            stats_por_serie=stats_por_serie,
            stats_por_nivel=stats_por_nivel,
            escola_nome=current_user.escola.nome,
            data_geracao=datetime.now()
        )

        # 6. Gerar o PDF e retornar a resposta
        pdf = HTML(string=html_renderizado).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=relatorio_saude_banco_questoes.pdf'

        log_audit('REPORT_GENERATED', details={'report_type': 'saude_banco_questoes'})
        return response

    except Exception as e:
        print(f"ERRO ao gerar relatório de saúde do banco de questões: {e}")
        flash("Ocorreu um erro inesperado ao gerar o relatório. Tente novamente.", "danger")
        return redirect(url_for('main_routes.painel_relatorios'))

@main_routes.route('/admin/relatorios/comparativo_turmas', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_comparativo_turmas():
    """
    Gera um relatório PDF comparando o desempenho de diferentes turmas
    em um mesmo Modelo de Avaliação.
    """
    try:
        # 1. Obter os filtros do formulário
        modelo_id = request.form.get('modelo_id', type=int)
        ano_letivo_id = request.form.get('ano_letivo_id', type=int)

        if not all([modelo_id, ano_letivo_id]):
            flash('Modelo de avaliação e ano letivo são obrigatórios para gerar este relatório.', 'danger')
            return redirect(url_for('main_routes.painel_relatorios'))

        # 2. Buscar informações para o cabeçalho do relatório
        modelo = ModeloAvaliacao.query.get(modelo_id)
        ano_letivo = AnoLetivo.query.get(ano_letivo_id)
        if not modelo or not ano_letivo or modelo.escola_id != current_user.escola_id:
            abort(404)

        # 3. Consulta agregada para calcular as estatísticas por turma (Série)
        #    Apenas resultados 'Finalizado' são considerados para as estatísticas.
        #    A função stddev_samp calcula o desvio padrão (sample standard deviation).
        #    Nota: A disponibilidade de func.stddev_samp pode depender do seu banco de dados (funciona no PostgreSQL).
        stats_por_turma = db.session.query(
            Serie.nome,
            func.count(Resultado.id).label('num_participantes'),
            func.avg(Resultado.nota).label('media_notas'),
            func.max(Resultado.nota).label('maior_nota'),
            func.min(Resultado.nota).label('menor_nota'),
            func.stddev_samp(Resultado.nota).label('desvio_padrao')
        ).join(Avaliacao, Resultado.avaliacao_id == Avaliacao.id
        ).join(Serie, Avaliacao.serie_id == Serie.id
        ).filter(
            Avaliacao.modelo_id == modelo_id,
            Resultado.ano_letivo_id == ano_letivo_id,
            Avaliacao.escola_id == current_user.escola_id,
            Resultado.status == 'Finalizado'
        ).group_by(Serie.id).order_by(Serie.nome).all()

        if not stats_por_turma:
            flash('Nenhum resultado finalizado encontrado para os filtros selecionados. Não é possível gerar o relatório comparativo.', 'warning')
            return redirect(url_for('main_routes.painel_relatorios'))

        # 4. Renderizar o template HTML para o PDF
        html_renderizado = render_template(
            'app/reports/comparativo_turmas_pdf.html',
            modelo=modelo,
            ano_letivo=ano_letivo,
            stats_data=stats_por_turma,
            data_geracao=datetime.now()
        )

        # 5. Gerar o PDF e retornar a resposta
        pdf = HTML(string=html_renderizado).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=comparativo_turmas_{modelo.nome}.pdf'
        
        log_audit('REPORT_GENERATED', details={'report_type': 'comparativo_turmas', 'filters': f'Modelo ID: {modelo_id}'})
        return response

    except Exception as e:
        print(f"ERRO ao gerar relatório comparativo de turmas: {e}")
        flash("Ocorreu um erro inesperado ao gerar o relatório. Tente novamente.", "danger")
        return redirect(url_for('main_routes.painel_relatorios'))

@main_routes.route('/admin/relatorios/alunos_por_serie', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_alunos_por_serie():
    """
    Gera um relatório PDF com a lista de todos os alunos matriculados
    em uma série/turma específica em um determinado ano letivo.
    """
    try:
        # 1. Obter os filtros do formulário
        serie_id = request.form.get('serie_id', type=int)
        ano_letivo_id = request.form.get('ano_letivo_id', type=int)

        if not all([serie_id, ano_letivo_id]):
            flash('Série e ano letivo são obrigatórios para gerar este relatório.', 'danger')
            return redirect(url_for('main_routes.painel_relatorios'))

        # 2. Buscar informações para o cabeçalho e validar permissão
        serie = Serie.query.get(serie_id)
        ano_letivo = AnoLetivo.query.get(ano_letivo_id)
        if not serie or not ano_letivo or serie.escola_id != current_user.escola_id:
            abort(404)

        # 3. Buscar todos os alunos matriculados na série e ano letivo especificados.
        #    A tabela Matricula é a fonte perfeita para esta informação.
        #    Usamos joinedload para já carregar os dados do aluno e ordenamos pelo nome.
        matriculas = Matricula.query.options(
            joinedload(Matricula.aluno)
        ).filter_by(
            serie_id=serie_id,
            ano_letivo_id=ano_letivo_id
        ).join(Usuario).order_by(Usuario.nome).all()

        if not matriculas:
            flash(f'Nenhum aluno encontrado para a turma "{serie.nome}" no ano de {ano_letivo.ano}.', 'warning')
            return redirect(url_for('main_routes.painel_relatorios'))

        # 4. Renderizar o template HTML para o PDF
        html_renderizado = render_template(
            'app/reports/lista_alunos_pdf.html',
            serie=serie,
            ano_letivo=ano_letivo,
            matriculas=matriculas,
            data_geracao=datetime.now()
        )

        # 5. Gerar o PDF e retornar a resposta
        pdf = HTML(string=html_renderizado).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=lista_alunos_{serie.nome}.pdf'
        
        log_audit('REPORT_GENERATED', details={'report_type': 'lista_alunos_por_serie', 'filters': f'Série ID: {serie_id}'})
        return response

    except Exception as e:
        print(f"ERRO ao gerar relatório de alunos por série: {e}")
        flash("Ocorreu um erro inesperado ao gerar o relatório. Tente novamente.", "danger")
        return redirect(url_for('main_routes.painel_relatorios'))

@main_routes.route('/admin/relatorios/professores')
@login_required
@role_required('coordenador')
def relatorio_professores():
    """
    Gera um relatório PDF com a lista de todos os professores da escola,
    incluindo as disciplinas e turmas que lecionam.
    """
    try:
        escola_id = current_user.escola_id

        # 1. Busca todos os professores da escola.
        #    Usamos 'subqueryload' para carregar de forma eficiente as listas de
        #    disciplinas e séries de cada professor em queries separadas,
        #    o que é ideal para relações "muitos-para-muitos".
        professores = Usuario.query.options(
            subqueryload(Usuario.disciplinas_lecionadas),
            subqueryload(Usuario.series_lecionadas)
        ).filter_by(
            escola_id=escola_id,
            role='professor'
        ).order_by(Usuario.nome).all()

        # 2. Renderizar o template HTML para o PDF
        html_renderizado = render_template(
            'app/reports/lista_professores_pdf.html',
            professores=professores,
            escola_nome=current_user.escola.nome,
            data_geracao=datetime.now()
        )

        # 3. Gerar o PDF e retornar a resposta
        pdf = HTML(string=html_renderizado).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=lista_de_professores.pdf'

        log_audit('REPORT_GENERATED', details={'report_type': 'lista_professores'})
        return response

    except Exception as e:
        print(f"ERRO ao gerar relatório de professores: {e}")
        flash("Ocorreu um erro inesperado ao gerar o relatório. Tente novamente.", "danger")
        return redirect(url_for('main_routes.painel_relatorios'))


@main_routes.route('/admin/relatorios/resultado_simulado', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_resultado_simulado():
    """
    Gera um relatório PDF com o resultado geral (ranking) de todos os alunos
    que participaram de um simulado (baseado em um Modelo de Avaliação).
    """
    try:
        # 1. Obter os filtros do formulário
        modelo_id = request.form.get('modelo_id', type=int)
        ano_letivo_id = request.form.get('ano_letivo_id', type=int)

        if not all([modelo_id, ano_letivo_id]):
            flash('Modelo de avaliação e ano letivo são obrigatórios para gerar este relatório.', 'danger')
            return redirect(url_for('main_routes.painel_relatorios'))

        # 2. Buscar informações para o cabeçalho e validar permissão
        modelo = ModeloAvaliacao.query.get(modelo_id)
        ano_letivo = AnoLetivo.query.get(ano_letivo_id)
        if not modelo or not ano_letivo or modelo.escola_id != current_user.escola_id:
            abort(404)

        # 3. Buscar todos os resultados finalizados para este simulado, ordenados por nota.
        #    A ordenação é a chave para este relatório.
        resultados = Resultado.query.options(
            joinedload(Resultado.aluno),
            joinedload(Resultado.avaliacao)
        ).join(Avaliacao).filter(
            Avaliacao.modelo_id == modelo_id,
            Resultado.ano_letivo_id == ano_letivo_id,
            Avaliacao.escola_id == current_user.escola_id,
            Resultado.status == 'Finalizado'
        ).order_by(Resultado.nota.desc(), Usuario.nome.asc()).all() # Ordena por nota (maior primeiro), e nome como desempate

        if not resultados:
            flash(f'Nenhum resultado finalizado encontrado para o simulado "{modelo.nome}".', 'warning')
            return redirect(url_for('main_routes.painel_relatorios'))

        # 4. Renderizar o template HTML para o PDF
        html_renderizado = render_template(
            'app/reports/resultado_simulado_pdf.html',
            modelo=modelo,
            ano_letivo=ano_letivo,
            resultados=resultados,
            data_geracao=datetime.now()
        )

        # 5. Gerar o PDF e retornar a resposta
        pdf = HTML(string=html_renderizado).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=resultado_simulado_{modelo.nome}.pdf'
        
        log_audit('REPORT_GENERATED', details={'report_type': 'resultado_simulado', 'filters': f'Modelo ID: {modelo_id}'})
        return response

    except Exception as e:
        print(f"ERRO ao gerar relatório de resultado de simulado: {e}")
        flash("Ocorreu um erro inesperado ao gerar o relatório. Tente novamente.", "danger")
        return redirect(url_for('main_routes.painel_relatorios'))

@main_routes.route('/admin/relatorios/boletim_aluno', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_boletim_aluno():
    """
    Gera um relatório PDF com o boletim de notas de um aluno específico
    para um determinado ano letivo, agrupando os resultados por disciplina.
    """
    try:
        # 1. Obter os filtros do formulário
        aluno_id = request.form.get('aluno_id', type=int)
        ano_letivo_id = request.form.get('ano_letivo_id', type=int)

        if not all([aluno_id, ano_letivo_id]):
            flash('Aluno e ano letivo são obrigatórios para gerar o boletim.', 'danger')
            return redirect(url_for('main_routes.painel_relatorios'))

        # 2. Buscar informações para o cabeçalho e validar permissão
        aluno = Usuario.query.get(aluno_id)
        ano_letivo = AnoLetivo.query.get(ano_letivo_id)
        if not aluno or not ano_letivo or aluno.escola_id != current_user.escola_id:
            abort(404)

        # 3. Buscar todos os resultados finalizados do aluno no ano letivo
        resultados = Resultado.query.options(
            joinedload(Resultado.avaliacao).joinedload(Avaliacao.disciplina)
        ).filter(
            Resultado.aluno_id == aluno_id,
            Resultado.ano_letivo_id == ano_letivo_id,
            Resultado.status == 'Finalizado',
            Resultado.nota.isnot(None)
        ).all()
        
        if not resultados:
            flash(f'Nenhum resultado finalizado encontrado para o aluno "{aluno.nome}" no ano de {ano_letivo.ano}.', 'warning')
            return redirect(url_for('main_routes.painel_relatorios'))

        # 4. Processar e agrupar os resultados por disciplina
        boletim_data = {}
        for res in resultados:
            # Apenas avaliações ligadas a uma disciplina entram no boletim
            if res.avaliacao and res.avaliacao.disciplina:
                disciplina = res.avaliacao.disciplina
                if disciplina.id not in boletim_data:
                    boletim_data[disciplina.id] = {
                        'nome_disciplina': disciplina.nome,
                        'avaliacoes': [],
                        'media_final': 0
                    }
                boletim_data[disciplina.id]['avaliacoes'].append({
                    'nome': res.avaliacao.nome,
                    'nota': res.nota
                })
        
        # Calcular a média final para cada disciplina
        for disc_id in boletim_data:
            notas = [av['nota'] for av in boletim_data[disc_id]['avaliacoes']]
            if notas:
                boletim_data[disc_id]['media_final'] = sum(notas) / len(notas)

        # 5. Renderizar o template HTML para o PDF
        html_renderizado = render_template(
            'app/reports/boletim_aluno_pdf.html',
            aluno=aluno,
            ano_letivo=ano_letivo,
            boletim_data=boletim_data.values(),
            data_geracao=datetime.now()
        )

        # 6. Gerar o PDF e retornar a resposta
        pdf = HTML(string=html_renderizado).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=boletim_{aluno.nome}.pdf'
        
        log_audit('REPORT_GENERATED', details={'report_type': 'boletim_aluno', 'filters': f'Aluno ID: {aluno_id}'})
        return response

    except Exception as e:
        print(f"ERRO ao gerar boletim do aluno: {e}")
        flash("Ocorreu um erro inesperado ao gerar o relatório. Tente novamente.", "danger")
        return redirect(url_for('main_routes.painel_relatorios'))

@main_routes.route('/responder_avaliacao/<int:avaliacao_id>', methods=['GET', 'POST'])
@login_required
@role_required('aluno')
def responder_avaliacao(avaliacao_id):
    """
    Lida com a exibição da prova para o aluno (GET) e o salvamento/finalização
    das respostas (POST).
    """
    # --- LÓGICA DO POST: Salvar ou Finalizar a Avaliação ---
    if request.method == 'POST':
        resultado = Resultado.query.filter_by(avaliacao_id=avaliacao_id, aluno_id=current_user.id).first_or_404()
        
        # Impede que uma prova já finalizada seja alterada
        if resultado.status == 'Finalizado':
            flash('Esta avaliação já foi finalizada e não pode ser alterada.', 'warning')
            return redirect(url_for('main_routes.meus_resultados'))

        try:
            # Mapeia as respostas já existentes para atualização
            respostas_existentes = {resp.questao_id: resp for resp in resultado.respostas}

            # Itera sobre todas as questões da avaliação para salvar as respostas
            for questao in resultado.avaliacao.questoes:
                resposta_aluno = request.form.get(f'q_{questao.id}')
                
                if resposta_aluno is not None: # Se o aluno respondeu a esta questão
                    if questao.id in respostas_existentes:
                        # Atualiza a resposta existente
                        respostas_existentes[questao.id].resposta_aluno = resposta_aluno
                    else:
                        # Cria uma nova resposta se for a primeira vez
                        nova_resposta = Resposta(
                            resultado_id=resultado.id,
                            questao_id=questao.id,
                            resposta_aluno=resposta_aluno
                        )
                        db.session.add(nova_resposta)
            
            # Verifica se o aluno clicou em "Finalizar"
            if 'finalizar' in request.form:
                # Calcula a nota preliminar (apenas para questões de múltipla escolha)
                nota_preliminar = 0
                for resposta in resultado.respostas:
                    if resposta.questao.tipo == 'multipla_escolha' and resposta.resposta_aluno == resposta.questao.gabarito:
                        nota_preliminar += 1.0 # ou o peso da questão, se houver
                
                resultado.nota = nota_preliminar
                resultado.status = 'Finalizado'
                resultado.data_realizacao = datetime.utcnow()
                flash('Avaliação finalizada com sucesso!', 'success')
                log_audit('ASSESSMENT_FINISHED', target_obj=resultado, details={'final_score': nota_preliminar})
            else:
                flash('Seu progresso foi salvo!', 'info')

            db.session.commit()
            return redirect(url_for('main_routes.meus_resultados'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao salvar suas respostas: {e}', 'danger')

    # --- LÓGICA DO GET: Exibir a Avaliação ---
    # Carrega a avaliação e o resultado do aluno
    resultado = Resultado.query.filter_by(avaliacao_id=avaliacao_id, aluno_id=current_user.id).first()
    avaliacao = Avaliacao.query.get_or_404(avaliacao_id)

    # Validação de acesso
    # Se for uma avaliação estática, o aluno precisa estar na lista de designados
    if not avaliacao.is_dinamica and current_user not in avaliacao.alunos_designados:
        flash('Você não tem permissão para acessar esta avaliação.', 'danger')
        return redirect(url_for('main_routes.dashboard'))

    # Se o resultado não existe (primeiro acesso a uma prova estática), cria um.
    if not resultado and not avaliacao.is_dinamica:
        ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
        resultado = Resultado(
            aluno_id=current_user.id,
            avaliacao_id=avaliacao.id,
            ano_letivo_id=ano_letivo_ativo.id if ano_letivo_ativo else None,
            status='Iniciada'
        )
        db.session.add(resultado)
        db.session.commit()
        log_audit('STATIC_ASSESSMENT_STARTED', target_obj=resultado)

    if not resultado:
        # Se mesmo assim não houver resultado (ex: aluno tentando acessar URL de prova dinâmica de outro)
        flash('Avaliação não encontrada ou não iniciada.', 'danger')
        return redirect(url_for('main_routes.listar_modelos_avaliacao'))

    # Impede o acesso se já estiver finalizada
    if resultado.status == 'Finalizado':
        flash('Esta avaliação já foi finalizada. Você pode ver seu resultado na lista abaixo.', 'info')
        return redirect(url_for('main_routes.ver_resultado_detalhado', resultado_id=resultado.id))

    # Mapeia as respostas já salvas para preencher o formulário
    respostas_map = {resp.questao_id: resp.resposta_aluno for resp in resultado.respostas}

    return render_template(
        'app/responder_avaliacao.html', 
        avaliacao=resultado.avaliacao, 
        respostas_map=respostas_map
    )

# ### ROTAS ANTIGAS DE API (MANTIDAS NO BLUEPRINT WEB POR ENQUANTO) ###
@main_routes.route('/api/conteudo_simulado/<int:serie_id>')
@login_required
@role_required('professor', 'coordenador') # Adicionado para segurança
def get_conteudo_simulado_por_serie(serie_id):
    """
    API para buscar as disciplinas e os assuntos disponíveis
    no banco de questões para uma determinada série.
    Usado para montar a tela de criação de simulados.
    """
    try:
        # Garante que a série pertence à escola do usuário
        serie = Serie.query.filter_by(id=serie_id, escola_id=current_user.escola_id).first_or_404()
        
        # Pega os IDs das disciplinas associadas a esta série
        disciplina_ids = [d.id for d in serie.disciplinas]
        
        # Busca todos os assuntos distintos para as disciplinas encontradas
        questoes_data = db.session.query(
            Questao.disciplina_id,
            Disciplina.nome.label('disciplina_nome'),
            Questao.assunto
        ).join(Disciplina, Questao.disciplina_id == Disciplina.id
        ).filter(
            Questao.disciplina_id.in_(disciplina_ids),
            Questao.serie_id == serie_id # Garante que as questões são da série correta
        ).distinct().all()

        # Organiza os dados em um dicionário para agrupar assuntos por disciplina
        disciplinas_com_assuntos = {}
        for q in questoes_data:
            if q.disciplina_id not in disciplinas_com_assuntos:
                disciplinas_com_assuntos[q.disciplina_id] = {
                    'id': q.disciplina_id,
                    'nome': q.disciplina_nome,
                    'assuntos': []
                }
            if q.assunto: # Evita adicionar assuntos nulos
                disciplinas_com_assuntos[q.disciplina_id]['assuntos'].append(q.assunto)

        return jsonify(list(disciplinas_com_assuntos.values()))

    except Exception as e:
        print(f"ERRO em /api/conteudo_simulado: {e}")
        return jsonify({'error': 'Erro ao buscar conteúdo do simulado'}), 500

@main_routes.route('/api/assuntos')
@login_required
@role_required('professor', 'coordenador') # Adicionado para segurança
def get_assuntos_por_disciplina_e_serie():
    """
    API que retorna uma lista de assuntos distintos baseada na disciplina e série
    fornecidas como parâmetros na URL.
    Usado na criação de provas de disciplina única.
    """
    try:
        disciplina_id = request.args.get('disciplina_id', type=int)
        serie_id = request.args.get('serie_id', type=int)

        if not disciplina_id or not serie_id:
            return jsonify({'error': 'ID da disciplina e da série são obrigatórios'}), 400

        # A query busca os assuntos distintos, garantindo que a disciplina
        # pertence à escola do usuário logado para segurança.
        assuntos_query = db.session.query(Questao.assunto).join(
            Disciplina, Questao.disciplina_id == Disciplina.id
        ).filter(
            Questao.disciplina_id == disciplina_id,
            Questao.serie_id == serie_id,
            Disciplina.escola_id == current_user.escola_id
        ).distinct().order_by(Questao.assunto).all()
        
        # Converte a lista de tuplas em uma lista de strings
        assuntos_list = [item[0] for item in assuntos_query if item[0]]

        return jsonify({'assuntos': assuntos_list})

    except Exception as e:
        print(f"ERRO em /api/assuntos: {e}")
        return jsonify({'error': 'Erro ao buscar assuntos'}), 500

@main_routes.route('/api/alunos_por_serie/<int:serie_id>')
@login_required
@role_required('coordenador', 'professor') # Professor também pode precisar disso
def api_alunos_por_serie(serie_id):
    """
    API que retorna uma lista de alunos (ID e Nome) matriculados
    em uma série específica no ano letivo ativo.
    """
    try:
        ano_letivo_ativo = AnoLetivo.query.filter_by(escola_id=current_user.escola_id, status='ativo').first()
        if not ano_letivo_ativo:
            return jsonify({'error': 'Nenhum ano letivo ativo encontrado'}), 404

        # Busca os alunos através da tabela de Matrícula
        matriculas = Matricula.query.options(
            joinedload(Matricula.aluno)
        ).filter_by(
            serie_id=serie_id,
            ano_letivo_id=ano_letivo_ativo.id
        ).join(Usuario).order_by(Usuario.nome).all()

        # Formata a saída em um JSON simples
        alunos_list = [{'id': m.aluno.id, 'nome': m.aluno.nome} for m in matriculas]
        
        return jsonify(alunos=alunos_list)

    except Exception as e:
        print(f"ERRO em /api/alunos_por_serie: {e}")
        return jsonify({'error': 'Erro ao buscar alunos'}), 500

# ===================================================================
# SEÇÃO 7: REGISTRO DOS BLUEPRINTS E EXECUÇÃO
# ===================================================================

# Registra os blueprints na aplicação principal para que as rotas
# definidas neles se tornem ativas.
app.register_blueprint(main_routes)
app.register_blueprint(api_v1)

# Bloco de execução padrão para rodar a aplicação Flask
if __name__ == '__main__':
    with app.app_context():
        # Garante que todas as tabelas do banco de dados sejam criadas se não existirem.
        # Em produção, isso é geralmente manuseado pelas migrações.
        db.create_all()
    # Inicia o servidor de desenvolvimento.
    app.run(debug=True)