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
                "from": "Online Tests <onboarding@resend.dev>",
                "to": ["manoelbd2012@gmail.com"],
                "subject": f"Nova Mensagem de Contato de {nome}",
                "html": f"""...""", # Omitido para brevidade
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
    if request.method == 'POST':
        # ... Lógica de pesquisa e cadastro de usuários ...
        return redirect(url_for('main_routes.gerenciar_usuarios'))
    series = Serie.query.filter_by(escola_id=current_user.escola_id).order_by(Serie.nome).all()
    disciplinas = Disciplina.query.filter_by(escola_id=current_user.escola_id).order_by(Disciplina.nome).all()
    usuarios = Usuario.query.options(joinedload(Usuario.matriculas).joinedload(Matricula.serie)).filter_by(escola_id=current_user.escola_id).order_by(Usuario.nome).all()
    return render_template('app/gerenciar_usuarios.html', series=series, disciplinas=disciplinas, usuarios=usuarios)

@main_routes.route('/admin/editar_usuario/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('coordenador')
def editar_usuario(user_id):
    usuario = Usuario.query.options(joinedload(Usuario.disciplinas_lecionadas), joinedload(Usuario.series_lecionadas)).filter_by(id=user_id, escola_id=current_user.escola_id).first_or_404()
    if request.method == 'POST':
        # ... Lógica de edição de usuário ...
        return redirect(url_for('main_routes.gerenciar_usuarios'))
    # ... Lógica GET ...
    return render_template('app/editar_usuario.html', usuario=usuario) # Simplificado

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
    if request.method == 'POST':
        # ... Lógica de gerenciar séries e disciplinas ...
        return redirect(url_for('main_routes.gerenciar_academico'))
    series = Serie.query.filter_by(escola_id=current_user.escola_id).options(joinedload(Serie.disciplinas)).order_by(Serie.nome).all()
    disciplinas = Disciplina.query.filter_by(escola_id=current_user.escola_id).order_by(Disciplina.nome).all()
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
    if request.method == 'POST':
        # ... Lógica de criar modelo ...
        return redirect(url_for('main_routes.listar_modelos_avaliacao'))
    # ... Lógica GET ...
    return render_template('app/criar_modelo_avaliacao.html') # Simplificado

@main_routes.route('/iniciar-avaliacao/<int:modelo_id>')
@login_required
@role_required('aluno')
def iniciar_avaliacao_dinamica(modelo_id):
    # ... Lógica de iniciar avaliação ...
    return redirect(url_for('main_routes.responder_avaliacao', avaliacao_id=nova_avaliacao.id))

@main_routes.route('/modelos-avaliacoes')
@login_required
@role_required('aluno', 'professor', 'coordenador')
def listar_modelos_avaliacao():
    # ... Lógica de listar modelos e avaliações ...
    if current_user.role in ['coordenador', 'professor']:
        return render_template('app/listar_avaliacoes_geradas.html') # Simplificado
    else: # Aluno
        return render_template('app/listar_modelos_avaliacao.html') # Simplificado

@main_routes.route('/modelo-avaliacao/<int:modelo_id>/detalhes')
@login_required
@role_required('coordenador', 'professor')
def detalhes_modelo_avaliacao(modelo_id):
    # ... Lógica de detalhes ...
    return render_template('app/detalhes_modelo_avaliacao.html') # Simplificado

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
def listar_avaliacoes():
    # ... Lógica de listar avaliações (estáticas) ...
    return render_template('app/listar_avaliacoes.html') # Simplificado

@main_routes.route('/avaliacao/<int:avaliacao_id>/detalhes')
@login_required
@role_required('coordenador', 'professor')
def detalhes_avaliacao(avaliacao_id):
    # ... Lógica de detalhes de avaliação estática ...
    return render_template('app/detalhes_avaliacao.html') # Simplificado

@main_routes.route('/meus-resultados')
@login_required
@role_required('aluno')
def meus_resultados():
    # ... Lógica de resultados do aluno ...
    return render_template('app/meus_resultados.html') # Simplificado

@main_routes.route('/resultado/<int:resultado_id>')
@login_required
@role_required('aluno')
def ver_resultado_detalhado(resultado_id):
    resultado = Resultado.query.filter_by(id=resultado_id, aluno_id=current_user.id).first_or_404()
    return render_template('app/ver_resultado.html', resultado=resultado)

@main_routes.route('/correcao/avaliacao/<int:avaliacao_id>')
@login_required
@role_required('professor', 'coordenador')
def correcao_lista_alunos(avaliacao_id):
    # ... Lógica de listar alunos para correção ...
    return render_template('app/correcao_lista.html') # Simplificado

@main_routes.route('/correcao/resultado/<int:resultado_id>', methods=['GET', 'POST'])
@login_required
@role_required('professor', 'coordenador')
def corrigir_respostas(resultado_id):
    # ... Lógica de correção ...
    if request.method == 'POST':
        # ...
        return redirect(url_for('main_routes.detalhes_modelo_avaliacao', modelo_id=resultado.avaliacao.modelo_id))
    return render_template('app/correcao_respostas.html') # Simplificado

@main_routes.route('/admin/relatorios')
@login_required
@role_required('coordenador')
def painel_relatorios():
    # ... Lógica de carregar dados para o painel ...
    return render_template('app/painel_relatorios.html') # Simplificado

@main_routes.route('/admin/auditoria')
@login_required
@role_required('coordenador')
def painel_auditoria():
    # ... Lógica de auditoria ...
    return render_template('app/painel_auditoria.html') # Simplificado

@main_routes.route('/admin/relatorios/desempenho_por_assunto', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_desempenho_por_assunto():
    # ... Lógica de gerar PDF ...
    return response

@main_routes.route('/admin/relatorios/desempenho_por_nivel', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_desempenho_por_nivel():
    # ... Lógica de gerar PDF ...
    return response

@main_routes.route('/admin/relatorios/analise_de_itens', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_analise_de_itens():
    # ... Lógica de gerar PDF ...
    return response

@main_routes.route('/admin/relatorios/saude_banco_questoes')
@login_required
@role_required('coordenador')
def relatorio_saude_banco_questoes():
    # ... Lógica de gerar PDF ...
    return response

@main_routes.route('/admin/relatorios/comparativo_turmas', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_comparativo_turmas():
    # ... Lógica de gerar PDF ...
    return response

@main_routes.route('/admin/relatorios/alunos_por_serie', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_alunos_por_serie():
    # ... Lógica de gerar PDF ...
    return response

@main_routes.route('/admin/relatorios/professores')
@login_required
@role_required('coordenador')
def relatorio_professores():
    # ... Lógica de gerar PDF ...
    return response

@main_routes.route('/admin/relatorios/resultado_simulado', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_resultado_simulado():
    # ... Lógica de gerar PDF ...
    return response

@main_routes.route('/admin/relatorios/boletim_aluno', methods=['POST'])
@login_required
@role_required('coordenador')
def relatorio_boletim_aluno():
    # ... Lógica de gerar PDF ...
    return response

@main_routes.route('/responder_avaliacao/<int:avaliacao_id>', methods=['GET', 'POST'])
@login_required
@role_required('aluno')
def responder_avaliacao(avaliacao_id):
    # ... Lógica de responder avaliação ...
    if request.method == 'POST':
        return redirect(url_for('main_routes.meus_resultados'))
    return render_template('app/responder_avaliacao.html') # Simplificado

# ### ROTAS ANTIGAS DE API (MANTIDAS NO BLUEPRINT WEB POR ENQUANTO) ###
@main_routes.route('/api/conteudo_simulado/<int:serie_id>')
@login_required
def get_conteudo_simulado_por_serie(serie_id):
    # ... sua lógica original ...
    return jsonify(resultado_final)

@main_routes.route('/api/assuntos')
@login_required
def get_assuntos_por_disciplina_e_serie():
    # ... sua lógica original ...
    return jsonify({'assuntos': assuntos_list})

@main_routes.route('/api/alunos_por_serie/<int:serie_id>')
@login_required
@role_required('coordenador')
def api_alunos_por_serie(serie_id):
    # ... sua lógica original ...
    return jsonify(alunos=alunos_ordenados)

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