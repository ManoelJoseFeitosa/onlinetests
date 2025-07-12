--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: ano_letivo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ano_letivo (
    id integer NOT NULL,
    ano integer NOT NULL,
    status character varying(20) NOT NULL,
    escola_id integer NOT NULL
);


ALTER TABLE public.ano_letivo OWNER TO postgres;

--
-- Name: ano_letivo_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ano_letivo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ano_letivo_id_seq OWNER TO postgres;

--
-- Name: ano_letivo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ano_letivo_id_seq OWNED BY public.ano_letivo.id;


--
-- Name: avaliacao; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.avaliacao (
    id integer NOT NULL,
    nome character varying(150) NOT NULL,
    tipo character varying(20) DEFAULT 'prova'::character varying NOT NULL,
    tempo_limite integer,
    criador_id integer NOT NULL,
    disciplina_id integer,
    serie_id integer,
    escola_id integer NOT NULL,
    ano_letivo_id integer,
    is_dinamica boolean NOT NULL,
    modelo_id integer
);


ALTER TABLE public.avaliacao OWNER TO postgres;

--
-- Name: avaliacao_alunos_designados; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.avaliacao_alunos_designados (
    avaliacao_id integer NOT NULL,
    usuario_id integer NOT NULL
);


ALTER TABLE public.avaliacao_alunos_designados OWNER TO postgres;

--
-- Name: avaliacao_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.avaliacao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.avaliacao_id_seq OWNER TO postgres;

--
-- Name: avaliacao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.avaliacao_id_seq OWNED BY public.avaliacao.id;


--
-- Name: avaliacao_questoes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.avaliacao_questoes (
    avaliacao_id integer NOT NULL,
    questao_id integer NOT NULL
);


ALTER TABLE public.avaliacao_questoes OWNER TO postgres;

--
-- Name: disciplina; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.disciplina (
    id integer NOT NULL,
    nome character varying(100) NOT NULL,
    escola_id integer NOT NULL
);


ALTER TABLE public.disciplina OWNER TO postgres;

--
-- Name: disciplina_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.disciplina_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.disciplina_id_seq OWNER TO postgres;

--
-- Name: disciplina_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.disciplina_id_seq OWNED BY public.disciplina.id;


--
-- Name: escola; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.escola (
    id integer NOT NULL,
    nome character varying(150) NOT NULL,
    cnpj character varying(18),
    data_cadastro timestamp without time zone,
    status character varying(20) NOT NULL
);


ALTER TABLE public.escola OWNER TO postgres;

--
-- Name: escola_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.escola_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.escola_id_seq OWNER TO postgres;

--
-- Name: escola_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.escola_id_seq OWNED BY public.escola.id;


--
-- Name: matricula; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.matricula (
    id integer NOT NULL,
    aluno_id integer NOT NULL,
    serie_id integer NOT NULL,
    ano_letivo_id integer NOT NULL,
    status character varying(30) NOT NULL
);


ALTER TABLE public.matricula OWNER TO postgres;

--
-- Name: matricula_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.matricula_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.matricula_id_seq OWNER TO postgres;

--
-- Name: matricula_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.matricula_id_seq OWNED BY public.matricula.id;


--
-- Name: modelo_avaliacao; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.modelo_avaliacao (
    id integer NOT NULL,
    nome character varying(150) NOT NULL,
    tipo character varying(20) NOT NULL,
    tempo_limite integer,
    criador_id integer NOT NULL,
    serie_id integer NOT NULL,
    escola_id integer NOT NULL,
    regras_selecao json NOT NULL
);


ALTER TABLE public.modelo_avaliacao OWNER TO postgres;

--
-- Name: modelo_avaliacao_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.modelo_avaliacao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.modelo_avaliacao_id_seq OWNER TO postgres;

--
-- Name: modelo_avaliacao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.modelo_avaliacao_id_seq OWNED BY public.modelo_avaliacao.id;


--
-- Name: professor_disciplinas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.professor_disciplinas (
    usuario_id integer NOT NULL,
    disciplina_id integer NOT NULL
);


ALTER TABLE public.professor_disciplinas OWNER TO postgres;

--
-- Name: professor_series; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.professor_series (
    usuario_id integer NOT NULL,
    serie_id integer NOT NULL
);


ALTER TABLE public.professor_series OWNER TO postgres;

--
-- Name: questao; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.questao (
    id integer NOT NULL,
    disciplina_id integer NOT NULL,
    serie_id integer NOT NULL,
    criador_id integer NOT NULL,
    assunto character varying(200) NOT NULL,
    tipo character varying(50) NOT NULL,
    texto text NOT NULL,
    imagem_nome character varying(255),
    imagem_alt character varying(500),
    nivel character varying(10) DEFAULT 'media'::character varying NOT NULL,
    opcao_a text,
    opcao_b text,
    opcao_c text,
    opcao_d text,
    gabarito character varying(1),
    justificativa_gabarito text
);


ALTER TABLE public.questao OWNER TO postgres;

--
-- Name: COLUMN questao.imagem_alt; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.questao.imagem_alt IS 'Texto alternativo para acessibilidade';


--
-- Name: COLUMN questao.nivel; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.questao.nivel IS 'Nível de dificuldade (facil, media, dificil)';


--
-- Name: questao_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.questao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.questao_id_seq OWNER TO postgres;

--
-- Name: questao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.questao_id_seq OWNED BY public.questao.id;


--
-- Name: resposta; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.resposta (
    id integer NOT NULL,
    resultado_id integer NOT NULL,
    questao_id integer NOT NULL,
    resposta_aluno text,
    status_correcao character varying(20),
    pontos double precision,
    feedback_professor text
);


ALTER TABLE public.resposta OWNER TO postgres;

--
-- Name: resposta_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.resposta_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.resposta_id_seq OWNER TO postgres;

--
-- Name: resposta_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.resposta_id_seq OWNED BY public.resposta.id;


--
-- Name: resultado; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.resultado (
    id integer NOT NULL,
    nota double precision,
    status character varying(50),
    data_realizacao timestamp without time zone NOT NULL,
    aluno_id integer NOT NULL,
    avaliacao_id integer NOT NULL,
    ano_letivo_id integer
);


ALTER TABLE public.resultado OWNER TO postgres;

--
-- Name: resultado_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.resultado_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.resultado_id_seq OWNER TO postgres;

--
-- Name: resultado_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.resultado_id_seq OWNED BY public.resultado.id;


--
-- Name: serie; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.serie (
    id integer NOT NULL,
    nome character varying(100) NOT NULL,
    escola_id integer NOT NULL
);


ALTER TABLE public.serie OWNER TO postgres;

--
-- Name: serie_disciplinas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.serie_disciplinas (
    serie_id integer NOT NULL,
    disciplina_id integer NOT NULL
);


ALTER TABLE public.serie_disciplinas OWNER TO postgres;

--
-- Name: serie_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.serie_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.serie_id_seq OWNER TO postgres;

--
-- Name: serie_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.serie_id_seq OWNED BY public.serie.id;


--
-- Name: simulado_disciplinas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.simulado_disciplinas (
    avaliacao_id integer NOT NULL,
    disciplina_id integer NOT NULL
);


ALTER TABLE public.simulado_disciplinas OWNER TO postgres;

--
-- Name: usuario; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usuario (
    id integer NOT NULL,
    nome character varying(150) NOT NULL,
    email character varying(150) NOT NULL,
    password character varying(256) NOT NULL,
    role character varying(50) NOT NULL,
    precisa_trocar_senha boolean NOT NULL,
    escola_id integer,
    is_superadmin boolean NOT NULL
);


ALTER TABLE public.usuario OWNER TO postgres;

--
-- Name: usuario_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.usuario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.usuario_id_seq OWNER TO postgres;

--
-- Name: usuario_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.usuario_id_seq OWNED BY public.usuario.id;


--
-- Name: ano_letivo id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ano_letivo ALTER COLUMN id SET DEFAULT nextval('public.ano_letivo_id_seq'::regclass);


--
-- Name: avaliacao id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao ALTER COLUMN id SET DEFAULT nextval('public.avaliacao_id_seq'::regclass);


--
-- Name: disciplina id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.disciplina ALTER COLUMN id SET DEFAULT nextval('public.disciplina_id_seq'::regclass);


--
-- Name: escola id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.escola ALTER COLUMN id SET DEFAULT nextval('public.escola_id_seq'::regclass);


--
-- Name: matricula id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matricula ALTER COLUMN id SET DEFAULT nextval('public.matricula_id_seq'::regclass);


--
-- Name: modelo_avaliacao id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.modelo_avaliacao ALTER COLUMN id SET DEFAULT nextval('public.modelo_avaliacao_id_seq'::regclass);


--
-- Name: questao id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questao ALTER COLUMN id SET DEFAULT nextval('public.questao_id_seq'::regclass);


--
-- Name: resposta id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.resposta ALTER COLUMN id SET DEFAULT nextval('public.resposta_id_seq'::regclass);


--
-- Name: resultado id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.resultado ALTER COLUMN id SET DEFAULT nextval('public.resultado_id_seq'::regclass);


--
-- Name: serie id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.serie ALTER COLUMN id SET DEFAULT nextval('public.serie_id_seq'::regclass);


--
-- Name: usuario id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario ALTER COLUMN id SET DEFAULT nextval('public.usuario_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
aef63bf217b4
\.


--
-- Data for Name: ano_letivo; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ano_letivo (id, ano, status, escola_id) FROM stdin;
1	2025	ativo	1
\.


--
-- Data for Name: avaliacao; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.avaliacao (id, nome, tipo, tempo_limite, criador_id, disciplina_id, serie_id, escola_id, ano_letivo_id, is_dinamica, modelo_id) FROM stdin;
1	MATEMATICA 1 - Adrian Guilherme Melo de Castro	prova	\N	5	1	1	1	1	t	5
2	MATEMATICA 2 - Adrian Guilherme Melo de Castro	prova	\N	5	1	1	1	1	t	6
3	MATEMATICA 3 - Adrian Guilherme Melo de Castro	prova	\N	5	1	1	1	1	t	7
4	INGLES 1 - Adrian Guilherme Melo de Castro	prova	\N	4	4	1	1	1	t	11
5	INGLES 2 - Adrian Guilherme Melo de Castro	prova	\N	4	4	1	1	1	t	12
6	BIOLOGIA 1 - Adrian Guilherme Melo de Castro	prova	\N	6	2	1	1	1	t	14
7	BIOLOGIA 2 - Adrian Guilherme Melo de Castro	prova	\N	6	2	1	1	1	t	15
8	MATEMATICA 1 - Ariel Arcangelo Alvarenga	prova	\N	5	1	1	1	1	t	5
\.


--
-- Data for Name: avaliacao_alunos_designados; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.avaliacao_alunos_designados (avaliacao_id, usuario_id) FROM stdin;
\.


--
-- Data for Name: avaliacao_questoes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.avaliacao_questoes (avaliacao_id, questao_id) FROM stdin;
1	71
1	68
1	70
1	74
1	72
1	65
2	96
2	97
2	93
2	99
2	95
3	85
3	81
3	87
3	84
3	91
4	57
4	54
4	56
4	58
4	55
5	53
5	51
5	50
5	52
5	49
6	134
6	102
6	121
6	127
6	135
7	130
7	116
7	119
7	118
7	114
8	73
8	64
8	65
8	80
8	74
8	72
\.


--
-- Data for Name: disciplina; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.disciplina (id, nome, escola_id) FROM stdin;
1	Matemática	1
2	Biologia	1
3	Língua Portuguesa	1
4	Inglês	1
5	Fundamentos de Tecnologia da Informação	1
6	Banco de Dados	1
7	Redes de Computadores	1
8	Lógica de Programação	1
\.


--
-- Data for Name: escola; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.escola (id, nome, cnpj, data_cadastro, status) FROM stdin;
1	Escola Teste	99999999/999-99	2025-07-10 14:16:25.618264	ativo
\.


--
-- Data for Name: matricula; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.matricula (id, aluno_id, serie_id, ano_letivo_id, status) FROM stdin;
1	7	1	1	cursando
2	8	1	1	cursando
3	9	1	1	cursando
4	10	1	1	cursando
5	11	1	1	cursando
6	12	2	1	cursando
7	13	2	1	cursando
8	14	2	1	cursando
9	15	2	1	cursando
10	16	2	1	cursando
\.


--
-- Data for Name: modelo_avaliacao; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.modelo_avaliacao (id, nome, tipo, tempo_limite, criador_id, serie_id, escola_id, regras_selecao) FROM stdin;
1	TI 1	prova	10	3	2	1	{"tipo": "prova", "disciplinas": [{"id": 6, "assuntos": ["Fundamentos de Banco de Dados", "SQL"], "niveis": {"facil": 3, "media": 1, "dificil": 1}}]}
2	TI 2	prova	10	3	2	1	{"tipo": "prova", "disciplinas": [{"id": 5, "assuntos": ["Hardware", "Software"], "niveis": {"facil": 2, "media": 2, "dificil": 1}}]}
3	TI 3	prova	10	3	2	1	{"tipo": "prova", "disciplinas": [{"id": 8, "assuntos": ["Algoritmo"], "niveis": {"facil": 3, "media": 1, "dificil": 1}}]}
4	SIMULADO 1	simulado	30	3	2	1	{"tipo": "simulado", "disciplinas": [{"id": 6, "assuntos": ["Fundamentos de Banco de Dados", "SQL"], "niveis": {"facil": 2, "media": 2, "dificil": 2}}, {"id": 5, "assuntos": ["Hardware", "Software"], "niveis": {"facil": 2, "media": 2, "dificil": 2}}, {"id": 8, "assuntos": ["Algoritmo"], "niveis": {"facil": 2, "media": 2, "dificil": 2}}, {"id": 7, "assuntos": ["Fundamentos de Redes"], "niveis": {"facil": 2, "media": 2, "dificil": 2}}]}
5	MATEMATICA 1	prova	10	5	1	1	{"tipo": "prova", "disciplinas": [{"id": 1, "assuntos": ["Algebra"], "niveis": {"facil": 3, "media": 2, "dificil": 1}}]}
6	MATEMATICA 2	prova	10	5	1	1	{"tipo": "prova", "disciplinas": [{"id": 1, "assuntos": ["Fun\\u00e7\\u00f5es"], "niveis": {"facil": 2, "media": 2, "dificil": 1}}]}
7	MATEMATICA 3	prova	10	5	1	1	{"tipo": "prova", "disciplinas": [{"id": 1, "assuntos": ["Geometria"], "niveis": {"facil": 2, "media": 2, "dificil": 1}}]}
8	LINGUA PORTUGUESA 1	prova	\N	4	1	1	{"tipo": "prova", "disciplinas": [{"id": 3, "assuntos": ["Verbo"], "niveis": {"facil": 2, "media": 2, "dificil": 1}}]}
9	LINGUA PORTUGUESA 2	prova	10	4	1	1	{"tipo": "prova", "disciplinas": [{"id": 3, "assuntos": ["Pronomes"], "niveis": {"facil": 2, "media": 2, "dificil": 1}}]}
10	LINGUA PORTUGUESA 3	prova	10	4	1	1	{"tipo": "prova", "disciplinas": [{"id": 3, "assuntos": ["An\\u00e1lise Sint\\u00e1tica"], "niveis": {"facil": 2, "media": 2, "dificil": 1}}]}
11	INGLES 1	prova	10	4	1	1	{"tipo": "prova", "disciplinas": [{"id": 4, "assuntos": ["Gram\\u00e1tica"], "niveis": {"facil": 2, "media": 2, "dificil": 1}}]}
12	INGLES 2	prova	10	4	1	1	{"tipo": "prova", "disciplinas": [{"id": 4, "assuntos": ["Verbo"], "niveis": {"facil": 2, "media": 2, "dificil": 1}}]}
13	INGLES 3	prova	10	4	1	1	{"tipo": "prova", "disciplinas": [{"id": 4, "assuntos": ["Vocabul\\u00e1rio"], "niveis": {"facil": 2, "media": 2, "dificil": 1}}]}
14	BIOLOGIA 1	prova	10	6	1	1	{"tipo": "prova", "disciplinas": [{"id": 2, "assuntos": ["Ecologia"], "niveis": {"facil": 2, "media": 2, "dificil": 1}}]}
15	BIOLOGIA 2	prova	10	6	1	1	{"tipo": "prova", "disciplinas": [{"id": 2, "assuntos": ["Fisiologia"], "niveis": {"facil": 2, "media": 2, "dificil": 1}}]}
16	BIOLOGIA 3	prova	10	6	1	1	{"tipo": "prova", "disciplinas": [{"id": 2, "assuntos": ["Gen\\u00e9tica"], "niveis": {"facil": 2, "media": 2, "dificil": 1}}]}
\.


--
-- Data for Name: professor_disciplinas; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.professor_disciplinas (usuario_id, disciplina_id) FROM stdin;
3	6
3	8
3	5
3	7
4	4
4	3
5	1
6	2
\.


--
-- Data for Name: professor_series; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.professor_series (usuario_id, serie_id) FROM stdin;
3	2
4	1
5	1
6	1
\.


--
-- Data for Name: questao; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.questao (id, disciplina_id, serie_id, criador_id, assunto, tipo, texto, imagem_nome, imagem_alt, nivel, opcao_a, opcao_b, opcao_c, opcao_d, gabarito, justificativa_gabarito) FROM stdin;
1	6	2	3	SQL	multipla_escolha	Qual das opções representa um comando DDL (Data Definition Language)?	\N	\N	facil	SELECT	INSERT	DELETE	CREATE	D	
2	6	2	3	Fundamentos de Banco de Dados	multipla_escolha	O que é uma chave primária em um banco de dados relacional?	Grafico1.webp	Gráfico de barras de demanda de perfil do consumidor com três barras coloridas. A azul é disposição a utilização e no eixo vertical atinge 72%, a amarela é fator decisivo na compra e atinge no eixo vertical 40% e a verde é fator decisivo por estilo que atinge no eixo vertical 35%	media	Um campo opcional usado para buscas	Um campo que aceita valores duplicados	Um identificador único para registros	Um índice automático	C	
3	6	2	3	SQL	multipla_escolha	Considere a estrutura: CREATE TABLE Cliente (id INT PRIMARY KEY, nome VARCHAR(100)). O que ocorrerá se tentarmos inserir dois registros com o mesmo id?	\N	\N	dificil	Ambos serão inseridos normalmente	O segundo substituirá o primeiro	O banco permitirá se o nome for diferente	O banco gerará um erro de violação de chave	D	
4	7	2	3	Fundamentos de Redes	multipla_escolha	Qual é a função do protocolo TCP?	\N	\N	facil	Criar conexões seguras entre dispositivos Bluetooth	Gerenciar endereços IP	Garantir entrega confiável de dados	Atribuir nomes de domínio	C	
5	7	2	3	Fundamentos de Redes	multipla_escolha	Qual das opções é um endereço IP válido?	\N	\N	media	192.300.1.1	256.1.1.1	172.16.0.10	192.168.0.256	C	
6	7	2	3	Fundamentos de Redes	multipla_escolha	Sobre a máscara de sub-rede 255.255.255.240, é correto afirmar:	\N	\N	dificil	Ela permite até 16 redes com 254 hosts cada	Ela permite 14 hosts por sub-rede	Ela é usada apenas em redes IPv6	Ela é a máscara padrão da classe B	B	
7	8	2	3	Algoritmo	multipla_escolha	Qual estrutura é usada para repetir instruções enquanto uma condição for verdadeira?	\N	\N	facil	if	while	switch	return	B	
8	8	2	3	Algoritmo	multipla_escolha	Em pseudocódigo, o que será impresso?\r\njava\r\nCopiarEditar\r\nx ← 5\r\nse x > 2 então\r\n   escreva("Maior")\r\nsenão\r\n   escreva("Menor")	\N	\N	media	Menor	Maior	Erro	Nenhuma saída	B	
9	8	2	3	Algoritmo	multipla_escolha	Qual será o valor de soma ao final do código abaixo?\r\ncss\r\nCopiarEditar\r\nsoma ← 0\r\npara i de 1 até 4 faça\r\n    soma ← soma + i\r\nfimpara	\N	\N	dificil	4	10	5	6	B	
10	5	2	3	Hardware	multipla_escolha	O que é hardware?	Grafico1.webp	Gráfico de barras de demanda de perfil do consumidor com três barras coloridas. A azul é disposição a utilização e no eixo vertical atinge 72%, a amarela é fator decisivo na compra e atinge no eixo vertical 40% e a verde é fator decisivo por estilo que atinge no eixo vertical 35%	facil	Programas de computador	Interface gráfica do usuário	Parte física do computador	Sistema operacional	C	
11	5	2	3	Software	multipla_escolha	Qual das opções é um sistema operacional?	\N	\N	media	Excel	BIOS	Linux	PowerPoint	C	
12	5	2	3	Software	multipla_escolha	Qual dos seguintes componentes NÃO faz parte de um sistema operacional?	\N	\N	dificil	Gerenciador de arquivos	Kernel	Compilador	Gerenciador de processos	C	
13	6	2	3	SQL	verdadeiro_falso	A linguagem SQL é usada apenas para consultar dados.	\N	\N	facil	Verdadeiro	Falso	\N	\N	B	A SQL também é usada para definir, manipular e controlar dados (comandos DDL, DML, DCL).
14	6	2	3	Fundamentos de Banco de Dados	verdadeiro_falso	Relacionamentos entre tabelas são possíveis por meio de chaves estrangeiras.	\N	\N	media	Verdadeiro	Falso	\N	\N	A	A chave estrangeira estabelece uma ligação entre duas tabelas.
15	6	2	3	Fundamentos de Banco de Dados	verdadeiro_falso	A normalização busca eliminar redundâncias e inconsistências em bancos de dados.	\N	\N	media	Verdadeiro	Falso	\N	\N	A	Ela organiza os dados em tabelas com relações bem definidas.
16	7	2	3	Fundamentos de Redes	verdadeiro_falso	O protocolo HTTP é responsável pela transferência de arquivos entre servidores FTP.	\N	\N	facil	Verdadeiro	Falso	\N	\N	B	HTTP é usado para páginas web; FTP é para transferência de arquivos.
17	7	2	3	Fundamentos de Redes	verdadeiro_falso	O modelo OSI possui 7 camadas.	\N	\N	media	Verdadeiro	Falso	\N	\N	A	Essas camadas incluem física, enlace, rede, transporte, etc.
18	7	2	3	Fundamentos de Redes	verdadeiro_falso	O endereço MAC identifica unicamente uma máquina na internet.	\N	\N	dificil	Verdadeiro	Falso	\N	\N	B	Ele identifica a interface de rede localmente; não é único na Internet.
19	8	2	3	Algoritmo	verdadeiro_falso	Variáveis devem ser declaradas antes de serem utilizadas.	Grafico1.webp	Gráfico de barras de demanda de perfil do consumidor com três barras coloridas. A azul é disposição a utilização e no eixo vertical atinge 72%, a amarela é fator decisivo na compra e atinge no eixo vertical 40% e a verde é fator decisivo por estilo que atinge no eixo vertical 35%	facil	Verdadeiro	Falso	\N	\N	A	Declaração permite alocar memória e definir tipo.
20	8	2	3	Algoritmo	verdadeiro_falso	A estrutura de decisão if permite executar diferentes blocos de código conforme uma condição.	\N	\N	media	Verdadeiro	Falso	\N	\N	A	Ela avalia a condição e executa o bloco correspondente.
21	8	2	3	Algoritmo	verdadeiro_falso	Funções não podem retornar valores em linguagens de programação estruturada.	\N	\N	dificil	Verdadeiro	Falso	\N	\N	B	Elas podem retornar valores com comandos como return.
22	5	2	3	Hardware	verdadeiro_falso	Um pendrive é um dispositivo de entrada.	\N	\N	facil	Verdadeiro	Falso	\N	\N	B	Ele é um dispositivo de armazenamento (entrada e saída).
23	5	2	3	Software	verdadeiro_falso	Softwares de planilhas eletrônicas são usados para organizar dados e realizar cálculos.	\N	\N	media	Verdadeiro	Falso	\N	\N	A	Exemplo: Microsoft Excel.
24	5	2	3	cloud	verdadeiro_falso	A computação em nuvem depende exclusivamente de servidores locais.	\N	\N	dificil	Verdadeiro	Falso	\N	\N	B	Ela depende de servidores remotos acessados via internet.
25	6	2	3	Fundamentos de Banco de Dados	discursiva	Explique a diferença entre chave primária e chave estrangeira em um banco de dados relacional.	\N	\N	media	\N	\N	\N	\N	\N	A chave primária identifica unicamente cada registro de uma tabela, enquanto a chave estrangeira é usada para criar um vínculo com a chave primária de outra tabela.
26	6	2	3	Fundamentos de Banco de Dados	discursiva	Qual a importância da normalização em um banco de dados relacional?	\N	\N	media	\N	\N	\N	\N	\N	Evita redundância de dados, melhora a integridade e facilita manutenção e consultas.
27	7	2	3	Fundamentos de Redes	discursiva	Explique o que é uma rede local (LAN).	\N	\N	facil	\N	\N	\N	\N	\N	É uma rede restrita a um espaço geográfico limitado, como casa ou escritório, permitindo compartilhamento de recursos.
28	7	2	3	Fundamentos de Redes	discursiva	Qual a diferença entre endereço IP público e privado?	\N	\N	media	\N	\N	\N	\N	\N	IP público é acessível na internet, IP privado é usado em redes internas e não roteável externamente.
29	7	2	3	Fundamentos de Redes	discursiva	Como o modelo OSI pode ajudar no diagnóstico de problemas em redes de computadores?	\N	\N	dificil	\N	\N	\N	\N	\N	Ele permite isolar problemas por camada (física, rede, aplicação), facilitando a identificação do nível onde ocorreu a falha.
30	8	2	3	Algoritmo	discursiva	Qual a importância das estruturas de repetição em programas?	\N	\N	media	\N	\N	\N	\N	\N	Permitem automatizar tarefas repetitivas, reduzindo código e erros manuais.
31	3	1	4	Tempos Verbais	multipla_escolha	Qual forma verbal preenche corretamente a lacuna?\r\n"Se eu __________ mais tempo, teria ido ao cinema."	\N	\N	facil	tivesse	teria	tinha	tenho	A	
32	3	1	4	Tempos Verbais	verdadeiro_falso	No período "Quando cheguei, ela já jantara", o verbo "jantara" está no pretérito mais-que-perfeito.	\N	\N	media	Verdadeiro	Falso	\N	\N	A	"Jantara" é a forma simples do pretérito mais-que-perfeito, indicando ação anterior a outra no passado ("cheguei").
33	3	1	4	Tempos Verbais	discursiva	Explique por que o verbo "haver" é impessoal na frase "Deve haver muitos candidatos".	\N	\N	dificil	\N	\N	\N	\N	\N	"Haver" é impessoal (não tem sujeito) quando indica existência, permanecendo na 3ª pessoa do singular ("deve haver").
34	3	1	4	Pronomes	multipla_escolha	Assinale a alternativa com erro no uso pronominal:	\N	\N	media	Vou me inscrever no concurso.	Ela se machucou.	Vi ele na festa.	Devolva-me o livro.	C	
35	3	1	4	Pronomes	verdadeiro_falso	Em "Comprei este celular", o pronome "este" é demonstrativo e indica proximidade do falante.	\N		media	Verdadeiro	Falso	\N	\N	A	"Este" refere-se a algo próximo ao emissor (ex.: objeto que ele segura/apresenta).
36	3	1	4	Pronomes	discursiva	Diferencie "pronome relativo" de "conjunção integrante" usando exemplos.	\N	\N	dificil	\N	\N	\N	\N	\N	Pronome relativo (ex.: "O livro que li") retoma um antecedente e introduz oração subordinada adjetiva. Conjunção integrante (ex.: "Duvido que venha") inicia oração subordinada substantiva, sem retomar termo.
37	3	1	4	Análise Sintática	multipla_escolha	Em "Os alunos entregaram os trabalhos ao professor", a expressão os trabalhos ao professor é:	Grafico1.webp	Gráfico de barras de demanda de perfil do consumidor com três barras coloridas. A azul é disposição a utilização e no eixo vertical atinge 72%, a amarela é fator decisivo na compra e atinge no eixo vertical 40% e a verde é fator decisivo por estilo que atinge no eixo vertical 35%	media	Objeto direto	Objeto indireto	Adjunto adverbial	Complemento nominal	A	
38	3	1	4	Análise Sintática	verdadeiro_falso	Na frase "A notícia de sua promoção surpreendeu todos", o termo de sua promoção é adjunto adnominal.	\N	\N	media	Verdadeiro	Falso	\N	\N	A	"De sua promoção" especifica o núcleo do sujeito ("notícia"), caracterizando adjunto adnominal.
39	3	1	4	Análise Sintática	discursiva	Classifique o sujeito em: "É necessário que estudemos mais".	\N	\N	dificil	\N	\N	\N	\N	\N	Sujeito oracional (oração subordinada substantiva subjetiva: "que estudemos mais").
40	3	1	4	Pronomes	multipla_escolha	Em "Prometeram-lhe uma recompensa", o pronome "lhe" exerce função de:	\N	\N	media	Objeto direto	Objeto indireto	Sujeito	Adjunto adverbial	B	
41	3	1	4	Verbo	verdadeiro_falso	Em "Choveu muito ontem", o verbo "choveu" é impessoal e tem sujeito inexistente.	\N	\N	media	Verdadeiro	Falso	\N	\N	A	Verbos como "chover" são impessoais (sujeito ausente) quando indicam fenômenos naturais.
42	3	1	4	Pronomes	discursiva	Reescreva "Ela viu nós" conforme a norma padrão.	\N	\N	dificil	\N	\N	\N	\N	\N	"Ela nos viu" (pronome oblíquo "nos" substitui "nós" como objeto direto).
43	3	1	4	Tempos Verbais	multipla_escolha	Se eles __________, avise-me	Grafico1.webp	Gráfico de barras de demanda de perfil do consumidor com três barras coloridas. A azul é disposição a utilização e no eixo vertical atinge 72%, a amarela é fator decisivo na compra e atinge no eixo vertical 40% e a verde é fator decisivo por estilo que atinge no eixo vertical 35%	facil	vierem	virão	viessem	vem	A	
44	3	1	4	Tempos Verbais	multipla_escolha	Caso você __________ o relatório, informe-me.	\N	\N	dificil	terminar	terminasse	termine	terminou	C	
45	3	1	4	Pronomes	multipla_escolha	Isto é entre eu e __________.	\N	\N	media	tu	você	ti	te	C	
46	3	1	4	Pronomes	multipla_escolha	Não se __________ ofendido.	\N	\N	dificil	sinta	sente	sintam	sentem	A	
47	3	1	4	Análise Sintática	multipla_escolha	Em "O diretor considerou os alunos esforçados", o termo destacado é: 	\N	\N	media	Obj. direto 	Predicativo	Aposto	Adj. adnominal 	B	
48	3	1	4	Análise Sintática	multipla_escolha	"Sua falta de atenção preocupa." O sujeito é: 	\N	\N	dificil	Simples	Composto	Oracional	Inexistente	A	
49	4	1	4	Verbo	multipla_escolha	Choose the correct past tense of the verb “go”:	\N	\N	facil	goed	gone	went	go	C	
50	4	1	4	Verbo	multipla_escolha	Which sentence uses the Present Perfect correctly?	\N	\N	media	She have gone to the store.	She has go to the store.	She has gone to the store.	She gone to the store.	C	
51	4	1	4	Verbo	multipla_escolha	Identify the sentence in Future Perfect:	\N	\N	dificil	She will be studying.	She will study.	She had studied.	She will have studied.	D	
52	4	1	4	Verbo	multipla_escolha	Which sentence is in the Passive Voice?	\N	\N	media	They built a house.	A house was built.	They are building a house.	Build a house!	B	
53	4	1	4	Verbo	multipla_escolha	What is the correct “-ing” form of the verb “run”?	Grafico1.webp	Gráfico de barras de demanda de perfil do consumidor com três barras coloridas. A azul é disposição a utilização e no eixo vertical atinge 72%, a amarela é fator decisivo na compra e atinge no eixo vertical 40% e a verde é fator decisivo por estilo que atinge no eixo vertical 35%	facil	runing	running	runned	ranning	B	
54	4	1	4	Gramática	multipla_escolha	Choose the correct form:\r\n“He ____ a car.”	\N	\N	facil	have	has	haves	is	B	
55	4	1	4	Gramática	multipla_escolha	Which sentence is grammatically correct?	\N	\N	media	She don’t like apples.	She doesn’t likes apples.	She doesn’t like apples.	She not like apples.	C	
56	4	1	4	Gramática	multipla_escolha	Identify the correct use of the conditional sentence (Second Conditional):	\N	\N	dificil	If I will go, I would see her.	If I went, I would see her.	If I go, I see her.	If I would go, I would see her.	B	
57	4	1	4	Gramática	multipla_escolha	Which is a correct question in the Present Simple?	\N	\N	media	Do she likes pizza?	Does she like pizza?	She like pizza?	Does she likes pizza?	B	
58	4	1	4	Gramática	multipla_escolha	Choose the correct article:\r\n“___ apple a day keeps the doctor away.”	\N	\N	facil	A	An	The	No article needed	B	
59	4	1	4	Vocabulário	multipla_escolha	What’s the synonym of “happy”?	\N	\N	facil	Angry	Sad	Joyful	Bored	C	
60	4	1	4	Vocabulário	multipla_escolha	What does “expensive” mean?	\N	\N	media	Cheap	Costly	Broken	New	B	
61	4	1	4	Vocabulário	multipla_escolha	Which phrasal verb means “to cancel”?	\N	\N	dificil	Turn on	Give up	Call off	Take in	C	
62	4	1	4	Vocabulário	multipla_escolha	Which word is a verb?	\N	\N	facil	Teacher	Beautiful	Run	Quickly	C	
63	4	1	4	Vocabulário	multipla_escolha	Choose the correct meaning of “reliable”:	\N	\N	media	Funny	Lazy	 Trustworthy	Boring	C	
64	1	1	5	Algebra	multipla_escolha	Qual é o resultado da expressão: 2x + 3x - x, quando x = 5?	\N	\N	facil	20	25	30	35	A	
65	1	1	5	Algebra	multipla_escolha	Qual é o valor de x na equação: 3x - 7 = 8?	\N	\N	facil	3	5	7	9	B	
66	1	1	5	Algebra	multipla_escolha	Qual é a forma fatorada da expressão x² - 9?	\N	\N	media	(x-3)(x+3)	(x-3)(x-3)	(x+3)(x+3)	(x-9)(x+1)	A	
67	1	1	5	Algebra	multipla_escolha	Se a = 2 e b = -3, qual o valor de a²b - ab²?	\N	\N	media	6	-6	12	-12	B	
68	1	1	5	Algebra	multipla_escolha	Qual é a solução da equação quadrática x² - 5x + 6 = 0?	\N	\N	media	x=1 e x=4	x=2 e x=3	x=-2 e x=-3	x=0 e x=5	B	
69	1	1	5	Algebra	multipla_escolha	Para qual valor de k a equação x² + kx + 9 = 0 tem raízes reais e iguais?	\N	\N	dificil	6	-6	6 ou -6	3	C	
70	1	1	5	Algebra	multipla_escolha	Se x + 1/x = 3, qual é o valor de x² + 1/x²?	Grafico1.webp	Gráfico de barras de demanda de perfil do consumidor com três barras coloridas. A azul é disposição a utilização e no eixo vertical atinge 72%, a amarela é fator decisivo na compra e atinge no eixo vertical 40% e a verde é fator decisivo por estilo que atinge no eixo vertical 35%	dificil	7	9	11	13	A	
71	1	1	5	Algebra	verdadeiro_falso	A expressão (x-2)(x+2) é equivalente a x²-4.	\N	\N	facil	Verdadeiro	Falso	\N	\N	A	Sim, pois é a diferença de quadrados.
72	1	1	5	Algebra	verdadeiro_falso	A equação 2x + 5 = 15 tem solução x=10.	\N	\N	facil	Verdadeiro	Falso	\N	\N	B	2x=10 -> x=5, não 10.
73	1	1	5	Algebra	verdadeiro_falso	O conjunto solução da inequação 3x - 4 < 5 é x < 3.	\N	\N	media	Verdadeiro	Falso	\N	\N	A	3x<9 -> x<3.
74	1	1	5	Algebra	verdadeiro_falso	A soma das raízes da equação x² - 6x + 8 = 0 é 6.	\N	\N	media	Verdadeiro	Falso	\N	\N	A	Soma das raízes = -b/a = 6.
75	1	1	5	Algebra	verdadeiro_falso	Se a e b são números reais positivos, então (a+b)^2 = a^2 + b^2.	\N	\N	dificil	Verdadeiro	Falso	\N	\N	B	(a+b)^2 = a^2 + 2ab + b^2, que é diferente de a^2+b^2, a menos que ab=0.
76	1	1	5	Algebra	discursiva	Resolva a equação: 4x - 6 = 2x + 4.	\N	\N	facil	\N	\N	\N	\N	\N	4x - 6 = 2x + 4\r\n4x - 2x = 4 + 6\r\n2x = 10\r\nx = 5
77	1	1	5	Algebra	discursiva	Fatorize completamente a expressão: 2x² - 8.	\N	\N	media	\N	\N	\N	\N	\N	2x² - 8 = 2(x² - 4) = 2(x-2)(x+2)
78	1	1	5	Algebra	discursiva	Resolva o sistema de equações:\r\nx + y = 10\r\n2x - y = 5	\N	\N	media	\N	\N	\N	\N	\N	Somando as duas equações: 3x = 15 -> x=5.\r\nSubstituindo na primeira: 5+y=10 -> y=5.
79	1	1	5	Algebra	discursiva	Prove que a soma de três números inteiros consecutivos é sempre divisível por 3.	\N	\N	dificil	\N	\N	\N	\N	\N	Sejam os números: n, n+1, n+2.\r\nSoma = 3n+3 = 3(n+1), que é divisível por 3.
80	1	1	5	Algebra	discursiva	Encontre o valor de x na equação: 2^{x+1} = 8.	\N	\N	dificil	\N	\N	\N	\N	\N	2^{x+1} = 2^3\r\nx+1=3\r\nx=2
81	1	1	5	Geometria	multipla_escolha	Qual é o perímetro de um quadrado de lado 5 cm?	\N	\N	facil	10 cm	15 cm	20 cm	25 cm	C	
82	1	1	5	Geometria	multipla_escolha	Em um triângulo retângulo, os catetos medem 3 cm e 4 cm. Qual é a medida da hipotenusa?	\N	\N	facil	5 cm	6 cm	7 cm	8 cm	A	
83	1	1	5	Geometria	multipla_escolha	Qual é a área de um círculo de raio 3 cm? (use π=3.14)	\N	\N	media	9.42 cm²	18.84 cm²	28.26 cm²	37.68 cm²	C	
84	1	1	5	Geometria	multipla_escolha	Um cubo tem aresta de 4 cm. Qual é o seu volume?	\N	\N	media	16 cm³	32 cm³	64 cm³	128 cm³	C	
85	1	1	5	Geometria	multipla_escolha	Em um triângulo equilátero, cada ângulo interno mede:	\N	\N	media	45°	60°	90°	120°	B	
86	1	1	5	Geometria	multipla_escolha	A diagonal de um cubo de aresta 3 cm é:	\N	\N	dificil	3√2 cm	3√3 cm	6 cm	9 cm	B	
87	1	1	5	Geometria	multipla_escolha	Qual é a área total de um cilindro com raio da base 2 cm e altura 5 cm? (use π=3.14)	\N	\N	dificil	62.8 cm²	87.92 cm²	94.2 cm²	100.48 cm²	B	
88	1	1	5	Geometria	verdadeiro_falso	A soma dos ângulos internos de um triângulo é 180°.	\N	\N	facil	Verdadeiro	Falso	\N	\N	A	Sim, propriedade fundamental.
89	1	1	5	Geometria	verdadeiro_falso	Um quadrado é sempre um retângulo.	\N	\N	facil	Verdadeiro	Falso	\N	\N	A	Sim, porque um quadrado satisfaz a definição de retângulo (todos os ângulos retos).
90	1	1	5	Geometria	verdadeiro_falso	Dois triângulos com a mesma área são sempre congruentes.	\N	\N	media	Verdadeiro	Falso	\N	\N	B	Não, por exemplo, um triângulo de base 4 e altura 3 tem área 6, e outro de base 6 e altura 2 também tem área 6, mas não são congruentes.
91	1	1	5	Geometria	discursiva	Calcule a área de um retângulo com comprimento 8 cm e largura 5 cm.	\N	\N	facil	\N	\N	\N	\N	\N	Área = comprimento * largura = 8 * 5 = 40 cm².
92	1	1	5	Geometria	discursiva	Prove que a soma dos ângulos internos de um quadrilátero é 360°.	\N	\N	dificil	\N	\N	\N	\N	\N	Um quadrilátero pode ser dividido em dois triângulos. Cada triângulo tem soma 180°, então 2*180°=360°.
93	1	1	5	Funções	multipla_escolha	Qual é a imagem da função f(x)=x+1, quando x=2?	\N	\N	facil	1	2	3	4	C	
94	1	1	5	Funções	multipla_escolha	Qual das seguintes é uma função afim?	\N	\N	facil	f(x)=x²	f(x)=2x+1	f(x)=|x|	f(x)=1/x	B	
95	1	1	5	Funções	multipla_escolha	Qual é o vértice da parábola da função f(x)=x²-6x+5?	Grafico1.webp	Gráfico de barras de demanda de perfil do consumidor com três barras coloridas. A azul é disposição a utilização e no eixo vertical atinge 72%, a amarela é fator decisivo na compra e atinge no eixo vertical 40% e a verde é fator decisivo por estilo que atinge no eixo vertical 35%	media	(3, -4)	(3, 4)	(-3, -4)	(-3, 4)	A	
96	1	1	5	Funções	multipla_escolha	Se f(x)=2x-1 e g(x)=x², qual é f(g(2))?	\N	\N	media	1	3	7	9	C	
97	1	1	5	Funções	multipla_escolha	Qual é o domínio da função f(x)=1/(x-3)?	\N	\N	dificil	Todos os reais	Todos os reais exceto 0	Todos os reais exceto 3	Todos os reais maiores que 3	C	
98	1	1	5	Funções	multipla_escolha	A função f(x)=x³ é:	\N	\N	dificil	Par	Ímpar	Nem par nem ímpar	Constante	B	
99	1	1	5	Funções	verdadeiro_falso	A função f(x)=x² é uma função ímpar.	\N	\N	facil	Verdadeiro	Falso	\N	\N	B	f(-x)=(-x)²=x²=f(x) -> função par.
100	1	1	5	Funções	verdadeiro_falso	A função f(x)=|x| é derivável em x=0.	\N	\N	dificil	Verdadeiro	Falso	\N	\N	B	Não, porque em x=0 há um "bico" e a derivada não é contínua.
101	2	1	6	Ecologia	multipla_escolha	Qual das alternativas representa um exemplo de cadeia alimentar?	\N	\N	facil	Sol → Água → Planta	Planta → Gafanhoto → Sapo → Cobra	Pedra → Liquens → Cogumelo	Vento → Pólen → Abelha	B	
102	2	1	6	Ecologia	multipla_escolha	O que é um nicho ecológico?	\N	\N	media	O lugar físico onde vive um organismo	O papel funcional do organismo no ecossistema	O tipo de alimento consumido por um ser vivo	A camada de solo onde ocorrem as raízes	B	
103	2	1	6	Ecologia	multipla_escolha	Em uma pirâmide ecológica de biomassa, qual das afirmações é correta?	\N	\N	dificil	A biomassa aumenta nos níveis superiores	A biomassa é sempre igual em todos os níveis	A biomassa diminui nos níveis tróficos superiores	A biomassa só existe no nível dos consumidores	C	
104	2	1	6	Genética	multipla_escolha	Qual das opções representa corretamente um genótipo heterozigoto?	\N	\N	facil	AA	aa	Aa	aA (não existe)	C	
105	2	1	6	Genética	multipla_escolha	A hemofilia é uma doença ligada ao sexo. Isso significa que:	\N	\N	media	Afeta apenas mulheres	Está localizada no cromossomo Y	Está ligada ao cromossomo X	Afeta apenas homens	C	
106	2	1	6	Genética	multipla_escolha	Qual a porcentagem esperada de filhos com grupo sanguíneo O de pais heterozigotos A x B?	\N	\N	dificil	0%	25%	50%	75%	B	
107	2	1	6	Fisiologia	multipla_escolha	Qual o órgão responsável pela filtração do sangue?	\N	\N	facil	Coração	Pulmão	Fígado	Rim	D	
108	2	1	6	Fisiologia	multipla_escolha	No sistema digestório, qual enzima atua na digestão de proteínas no estômago?	\N	\N	media	Amilase salivar	Pepsina	Lipase	Maltase	B	
109	2	1	6	Fisiologia	multipla_escolha	A mielina tem função de:	\N	\N	dificil	Produzir hormônios	Aumentar a velocidade da condução do impulso nervoso	Atuar na contração muscular	Regular a pressão arterial	B	
110	2	1	6	Genética	multipla_escolha	O DNA é composto por:	\N	\N	facil	Aminoácidos	Glicerol	Nucleotídeos	Monossacarídeos	C	
111	2	1	6	Fisiologia	multipla_escolha	Os pulmões fazem parte de qual sistema?	\N	\N	media	Digestório	Circulatório	Excretor	Respiratório	D	
112	2	1	6	Genética	multipla_escolha	Qual a relação entre mutações genéticas e evolução?	\N	\N	media	Não há relação	Mutações impedem a evolução	Mutações fornecem variabilidade genética para a seleção natural	Mutações causam apenas doenças	C	
113	2	1	6	Ecologia	multipla_escolha	O que são consumidores primários?	\N	\N	facil	Plantas	Animais que comem plantas	Animais que comem carnívoros	Decompositores	B	
114	2	1	6	Fisiologia	multipla_escolha	A fotossíntese ocorre em que organela celular?	\N	\N	media	Mitocôndria	Núcleo	Ribossomo	Cloroplasto	D	
115	2	1	6	Fisiologia	multipla_escolha	Qual das alternativas representa uma adaptação fisiológica?	Grafico1.webp	Gráfico de barras de demanda de perfil do consumidor com três barras coloridas. A azul é disposição a utilização e no eixo vertical atinge 72%, a amarela é fator decisivo na compra e atinge no eixo vertical 40% e a verde é fator decisivo por estilo que atinge no eixo vertical 35%	dificil	Camuflagem	Produção de suor para resfriamento corporal	Migração	Mudança de coloração sazonal	B	
116	2	1	6	Fisiologia	multipla_escolha	O sistema nervoso central é formado por:	\N	\N	facil	Nervos e gânglios	Cérebro e medula espinhal	Coração e pulmões	Estômago e intestinos	B	
117	2	1	6	Genética	multipla_escolha	O que caracteriza a herança recessiva?	\N	\N	media	É expressa sempre que está presente	Só se manifesta em heterozigose	Se manifesta apenas em homozigose	Só aparece em filhos homens	C	
118	2	1	6	Fisiologia	multipla_escolha	Qual a função da válvula mitral no coração?	\N	\N	dificil	Impedir o refluxo entre átrio direito e ventrículo direito	Controlar a entrada de sangue no átrio esquerdo	Separar o átrio esquerdo do ventrículo esquerdo	Bombear sangue para os pulmões	C	
119	2	1	6	Fisiologia	multipla_escolha	Em qual fase do ciclo celular ocorre a duplicação do DNA?	\N	\N	media	Prófase	Metáfase	Anáfase	Interfase	D	
120	2	1	6	Ecologia	multipla_escolha	Quem são os principais produtores nos ecossistemas?	Grafico1.webp	Gráfico de barras de demanda de perfil do consumidor com três barras coloridas. A azul é disposição a utilização e no eixo vertical atinge 72%, a amarela é fator decisivo na compra e atinge no eixo vertical 40% e a verde é fator decisivo por estilo que atinge no eixo vertical 35%	facil	Animais	Fungos	Plantas e algas	Bactérias decompositoras	C	
121	2	1	6	Ecologia	verdadeiro_falso	A clorofila é responsável pela cor vermelha das flores.	\N	\N	facil	Verdadeiro	Falso	\N	\N	B	A clorofila é verde e atua na fotossíntese.
122	2	1	6	Genética	verdadeiro_falso	Os cromossomos sexuais determinam o sexo do indivíduo.	\N	\N	media	Verdadeiro	Falso	\N	\N	A	Os cromossomos X e Y são responsáveis pela determinação do 
123	2	1	6	Fisiologia	verdadeiro_falso	O sistema linfático atua apenas na digestão.	\N	\N	dificil	Verdadeiro	Falso	\N	\N	B	Atua no transporte de lipídios e defesa imunológica.
124	2	1	6	Fisiologia	verdadeiro_falso	A urina é produzida nos rins.	\N	\N	facil	Verdadeiro	Falso	\N	\N	A	Os rins filtram o sangue e formam a urina.
125	2	1	6	Fisiologia	verdadeiro_falso	As mitocôndrias são responsáveis pela respiração celular.	\N	\N	media	Verdadeiro	Falso	\N	\N	A	Produzem energia (ATP) através da respiração aeróbica.
126	2	1	6	Genética	verdadeiro_falso	Os genes dominantes são sempre mais vantajosos.	\N	\N	dificil	Verdadeiro	Falso	\N	\N	B	Vantagem ou desvantagem depende do ambiente, não da dominância.
127	2	1	6	Ecologia	verdadeiro_falso	As plantas realizam fotossíntese e respiração celular.	\N	\N	facil	Verdadeiro	Falso	\N	\N	A	zem e utilizam energia.
128	2	1	6	Genética	verdadeiro_falso	Um gene é composto por aminoácidos.	Grafico1.webp	Gráfico de barras de demanda de perfil do consumidor com três barras coloridas. A azul é disposição a utilização e no eixo vertical atinge 72%, a amarela é fator decisivo na compra e atinge no eixo vertical 40% e a verde é fator decisivo por estilo que atinge no eixo vertical 35%	media	Verdadeiro	Falso	\N	\N	B	Os genes são compostos por sequências de DNA.
129	2	1	6	Fisiologia	verdadeiro_falso	A pressão arterial é regulada exclusivamente pelo sistema digestivo.	\N	\N	dificil	Verdadeiro	Falso	\N	\N	B	Envolve o sistema cardiovascular, nervoso e endócrino.
130	2	1	6	Fisiologia	verdadeiro_falso	O pulmão é o principal órgão da respiração.	\N	\N	facil	Verdadeiro	Falso	\N	\N	A	Realiza trocas gasosas com o ambiente.
131	2	1	6	Genética	verdadeiro_falso	A variabilidade genética pode ser aumentada pela recombinação genética.	\N	\N	media	Verdadeiro	Falso	\N	\N	A	Ocorre na meiose e promove diversidade.
132	2	1	6	Fisiologia	verdadeiro_falso	A adrenalina é um hormônio que reduz a frequência cardíaca.	\N	\N	dificil	Verdadeiro	Falso	\N	\N	B	Ela aumenta a frequência cardíaca em situações de estresse.
133	2	1	6	Ecologia	discursiva	Explique o que é uma cadeia alimentar e dê um exemplo.	\N	\N	facil	\N	\N	\N	\N	\N	Cadeia alimentar é a sequência de transferência de energia entre os seres vivos. Exemplo: planta → coelho → raposa.
134	2	1	6	Ecologia	discursiva	Qual a importância dos decompositores nos ecossistemas?	\N	\N	media	\N	\N	\N	\N	\N	Reciclam matéria orgânica, devolvendo nutrientes ao solo.
135	2	1	6	Ecologia	discursiva	Explique o conceito de sucessão ecológica e cite uma situação em que ela ocorre.	\N	\N	dificil	\N	\N	\N	\N	\N	a substituição gradual de espécies em um ambiente. Exemplo: recuperação de floresta após incêndio.
136	2	1	6	Genética	discursiva	Explique a diferença entre genótipo e fenótipo.	\N	\N	media	\N	\N	\N	\N	\N	Genótipo: conjunto de genes; Fenótipo: características observáveis.
\.


--
-- Data for Name: resposta; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.resposta (id, resultado_id, questao_id, resposta_aluno, status_correcao, pontos, feedback_professor) FROM stdin;
1	1	71	V	incorreta	0	\N
2	1	68	B	correta	1	\N
3	1	70	A	correta	1	\N
4	1	74	F	incorreta	0	\N
5	1	72	F	incorreta	0	\N
6	1	65	B	correta	1	\N
7	2	96	C	correta	1	\N
8	2	97	C	correta	1	\N
9	2	93	B	incorreta	0	\N
10	2	99	F	incorreta	0	\N
11	2	95	C	incorreta	0	\N
12	3	85	A	incorreta	0	\N
13	3	81	D	incorreta	0	\N
14	3	87	C	incorreta	0	\N
15	3	84	B	incorreta	0	\N
17	3	85	A	incorreta	0	\N
18	3	81	D	incorreta	0	\N
19	3	87	D	incorreta	0	\N
20	3	84	B	incorreta	0	\N
22	4	57	B	correta	1	\N
23	4	54	B	correta	1	\N
24	4	56	B	correta	1	\N
25	4	58	B	correta	1	\N
26	4	55	C	correta	1	\N
27	5	53	B	correta	1	\N
28	5	51	C	incorreta	0	\N
29	5	50	B	incorreta	0	\N
30	5	52	B	correta	1	\N
31	5	49	B	incorreta	0	\N
33	6	102	A	incorreta	0	\N
34	6	121	F	incorreta	0	\N
35	6	127	V	incorreta	0	\N
37	7	130	V	incorreta	0	\N
38	7	116	B	correta	1	\N
39	7	119	C	incorreta	0	\N
40	7	118	B	incorreta	0	\N
41	7	114	A	incorreta	0	\N
16	3	91	sdfhdhfgjfjtyighfhsfghsfhg	correta	1	kjdfk.BDKCJBXVCJHAVC.JHASGFJadskjhdkfgjasdf
21	3	91	fagdgdsd	correta	1	hfjhvsdjfhgsdkjfkjdshvfhvdsjfhbdsjhfvsdjf
32	6	134	kxjbckv.zxbckzxcmzxnbcmzx	correta	1	teste de feedback do aluno
36	6	135	zcfghnxcvbcvbcc	correta	1	teste de feedback do aluno
42	8	73	V	incorreta	0	\N
43	8	64	C	incorreta	0	\N
44	8	65	B	correta	1	\N
46	8	74	V	incorreta	0	\N
47	8	72	V	incorreta	0	\N
45	8	80	fgdhfhfhfhgg	correta	1	teste de fedeback
\.


--
-- Data for Name: resultado; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.resultado (id, nota, status, data_realizacao, aluno_id, avaliacao_id, ano_letivo_id) FROM stdin;
1	5	Finalizado	2025-07-11 11:59:46.462846	7	1	1
2	4	Finalizado	2025-07-11 12:00:41.892007	7	2	1
4	10	Finalizado	2025-07-11 12:03:28.250768	7	4	1
5	4	Finalizado	2025-07-11 12:04:00.06814	7	5	1
7	2	Finalizado	2025-07-11 12:06:25.820553	7	7	1
3	4	Finalizado	2025-07-11 12:02:39.636539	7	3	1
6	4	Finalizado	2025-07-11 12:05:31.540397	7	6	1
8	3.33	Finalizado	2025-07-11 17:36:10.176746	8	8	1
\.


--
-- Data for Name: serie; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.serie (id, nome, escola_id) FROM stdin;
1	1° Série - Ensino Médio	1
2	Técnico em Desenvolvimento de Sistemas	1
\.


--
-- Data for Name: serie_disciplinas; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.serie_disciplinas (serie_id, disciplina_id) FROM stdin;
1	3
1	1
1	2
1	4
2	8
2	6
2	5
2	7
\.


--
-- Data for Name: simulado_disciplinas; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.simulado_disciplinas (avaliacao_id, disciplina_id) FROM stdin;
\.


--
-- Data for Name: usuario; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.usuario (id, nome, email, password, role, precisa_trocar_senha, escola_id, is_superadmin) FROM stdin;
1	Super Admin	manoelbd2012@gmail.com	pbkdf2:sha256:1000000$vdYVn8rRpSIEgStY$db60bf727677872e5bcca12e07c42db5fc197cd05e2d6b5b209fbe009d694c79	coordenador	f	\N	t
2	Coordenador Escola	coordenador@teste.com	pbkdf2:sha256:1000000$dv7S1xgnigZbd970$547878e4bf58fb763e8e9a7edac4c5c5622095570e03480aaf2be523ea0f46cb	coordenador	f	1	f
3	Manoel Feitosa	manoel@teste.com	pbkdf2:sha256:1000000$kBZQm74qpYFVoTxd$67619a34fc996508c7a1729804e92a5831817b625bc939f7bdbe26d5d51cddde	professor	f	1	f
4	Thaisa Castro	thaisa@teste.com	pbkdf2:sha256:1000000$DecYZcF2bg6mhEVP$0b56fb982adbf8074df853ca14aecb0c4c86409ca6bf1b20652f3409a8206f94	professor	f	1	f
5	Humberto Feitosa	humberto@teste.com	pbkdf2:sha256:1000000$aQFoOddm2TtmvPrI$0fc10a4191983fca457fea10e6dd421da6d846460195dab52016ceccc89f8869	professor	f	1	f
6	Isadora Feitosa	isadora@teste.com	pbkdf2:sha256:1000000$stdTd1qZtn5v68o9$fdf60b60b50cf0e26fe3320facd736985c321066d5087bc068b0bf280a29b18e	professor	f	1	f
7	Adrian Guilherme Melo de Castro	adrian@teste.com	pbkdf2:sha256:1000000$6FdlRwnedTkbm3iw$32ce0740d60f332faebe70b57bc60149c1c39a4be0d3af3eca67851cb652bf67	aluno	f	1	f
10	Carolina Martins Abreu	carolina@teste.com	pbkdf2:sha256:1000000$Jf7YrAUVVlp7fwxl$07d3f08065036857058f321120b79c2569577f058b99f7d6f4bf6e302d337ebe	aluno	f	1	f
9	Daniela Costa	daniela@teste.com	pbkdf2:sha256:1000000$tknzh8dY10OlDQHr$7af407c3654d5a743096d76dc8324eba1bf221ec27f13cd4ab88da7fa4fa7b71	aluno	f	1	f
11	Davi Oliveira Silva	davi@teste.com	pbkdf2:sha256:1000000$0lM8lpPmFDu2Uy3h$38144e6a99b8e364199e7189653299d820083868593a23c8f4020cd0c14d4e3f	aluno	f	1	f
8	Ariel Arcangelo Alvarenga	ariel@teste.com	pbkdf2:sha256:1000000$7oerVKnxdEpu4Y0E$5c6503799d9acddda51258cd53d1bb7b49c24f8c78a8b693745ad35e90875097	aluno	f	1	f
12	Ana Clarice Portela Reis	ana@teste.com	pbkdf2:sha256:1000000$H2AcUc6sa0ZxmKk0$74b997dc16383ac81353a5ab3b2358a1481edc0c930b9b447f4d85f30902623e	aluno	f	1	f
13	Cairo Daniel Escorcio dos Santos	cairo@teste.com	pbkdf2:sha256:1000000$thTSrXTnlLk52J4U$0ebbcdf460493cacdda84404890e50657e9e97370abc9539f035e5ed577ddc72	aluno	f	1	f
14	Enzo Camelo de Oliveira	enzo@teste.com	pbkdf2:sha256:1000000$8Y34md4yXkAc2XEN$b8c4f51724901c0d011cfba00ff6db93f59ce0fd1e0882d2a9c9b5e975bbde20	aluno	f	1	f
15	Gabriela Morais	gabriela@teste.com	pbkdf2:sha256:1000000$LDVSoyMJ5Ovd3YlL$2d3fddca597fecffd1b1ddc95c002713531dcf0c37f1564b28fbc9217b96b9e4	aluno	f	1	f
16	Geovana Yasmim Moreira Silva	geovana@teste.com	pbkdf2:sha256:1000000$QqmI6JM8rdXRX3HF$4ec5d19b9b77deebc1fd6d760a38a2d566e468b0e51a31b4ac9b21381c3126f3	aluno	f	1	f
\.


--
-- Name: ano_letivo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ano_letivo_id_seq', 1, true);


--
-- Name: avaliacao_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.avaliacao_id_seq', 8, true);


--
-- Name: disciplina_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.disciplina_id_seq', 8, true);


--
-- Name: escola_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.escola_id_seq', 1, true);


--
-- Name: matricula_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.matricula_id_seq', 10, true);


--
-- Name: modelo_avaliacao_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.modelo_avaliacao_id_seq', 16, true);


--
-- Name: questao_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.questao_id_seq', 136, true);


--
-- Name: resposta_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.resposta_id_seq', 47, true);


--
-- Name: resultado_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.resultado_id_seq', 8, true);


--
-- Name: serie_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.serie_id_seq', 2, true);


--
-- Name: usuario_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.usuario_id_seq', 16, true);


--
-- Name: ano_letivo _ano_escola_uc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ano_letivo
    ADD CONSTRAINT _ano_escola_uc UNIQUE (ano, escola_id);


--
-- Name: disciplina _nome_escola_uc_disciplina; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.disciplina
    ADD CONSTRAINT _nome_escola_uc_disciplina UNIQUE (nome, escola_id);


--
-- Name: serie _nome_escola_uc_serie; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.serie
    ADD CONSTRAINT _nome_escola_uc_serie UNIQUE (nome, escola_id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: ano_letivo ano_letivo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ano_letivo
    ADD CONSTRAINT ano_letivo_pkey PRIMARY KEY (id);


--
-- Name: avaliacao_alunos_designados avaliacao_alunos_designados_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao_alunos_designados
    ADD CONSTRAINT avaliacao_alunos_designados_pkey PRIMARY KEY (avaliacao_id, usuario_id);


--
-- Name: avaliacao avaliacao_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao
    ADD CONSTRAINT avaliacao_pkey PRIMARY KEY (id);


--
-- Name: avaliacao_questoes avaliacao_questoes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao_questoes
    ADD CONSTRAINT avaliacao_questoes_pkey PRIMARY KEY (avaliacao_id, questao_id);


--
-- Name: disciplina disciplina_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.disciplina
    ADD CONSTRAINT disciplina_pkey PRIMARY KEY (id);


--
-- Name: escola escola_cnpj_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.escola
    ADD CONSTRAINT escola_cnpj_key UNIQUE (cnpj);


--
-- Name: escola escola_nome_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.escola
    ADD CONSTRAINT escola_nome_key UNIQUE (nome);


--
-- Name: escola escola_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.escola
    ADD CONSTRAINT escola_pkey PRIMARY KEY (id);


--
-- Name: matricula matricula_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matricula
    ADD CONSTRAINT matricula_pkey PRIMARY KEY (id);


--
-- Name: modelo_avaliacao modelo_avaliacao_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.modelo_avaliacao
    ADD CONSTRAINT modelo_avaliacao_pkey PRIMARY KEY (id);


--
-- Name: professor_disciplinas professor_disciplinas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.professor_disciplinas
    ADD CONSTRAINT professor_disciplinas_pkey PRIMARY KEY (usuario_id, disciplina_id);


--
-- Name: professor_series professor_series_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.professor_series
    ADD CONSTRAINT professor_series_pkey PRIMARY KEY (usuario_id, serie_id);


--
-- Name: questao questao_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questao
    ADD CONSTRAINT questao_pkey PRIMARY KEY (id);


--
-- Name: resposta resposta_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.resposta
    ADD CONSTRAINT resposta_pkey PRIMARY KEY (id);


--
-- Name: resultado resultado_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.resultado
    ADD CONSTRAINT resultado_pkey PRIMARY KEY (id);


--
-- Name: serie_disciplinas serie_disciplinas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.serie_disciplinas
    ADD CONSTRAINT serie_disciplinas_pkey PRIMARY KEY (serie_id, disciplina_id);


--
-- Name: serie serie_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.serie
    ADD CONSTRAINT serie_pkey PRIMARY KEY (id);


--
-- Name: simulado_disciplinas simulado_disciplinas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.simulado_disciplinas
    ADD CONSTRAINT simulado_disciplinas_pkey PRIMARY KEY (avaliacao_id, disciplina_id);


--
-- Name: usuario usuario_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_email_key UNIQUE (email);


--
-- Name: usuario usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_pkey PRIMARY KEY (id);


--
-- Name: ano_letivo ano_letivo_escola_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ano_letivo
    ADD CONSTRAINT ano_letivo_escola_id_fkey FOREIGN KEY (escola_id) REFERENCES public.escola(id);


--
-- Name: avaliacao_alunos_designados avaliacao_alunos_designados_avaliacao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao_alunos_designados
    ADD CONSTRAINT avaliacao_alunos_designados_avaliacao_id_fkey FOREIGN KEY (avaliacao_id) REFERENCES public.avaliacao(id);


--
-- Name: avaliacao_alunos_designados avaliacao_alunos_designados_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao_alunos_designados
    ADD CONSTRAINT avaliacao_alunos_designados_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- Name: avaliacao avaliacao_ano_letivo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao
    ADD CONSTRAINT avaliacao_ano_letivo_id_fkey FOREIGN KEY (ano_letivo_id) REFERENCES public.ano_letivo(id);


--
-- Name: avaliacao avaliacao_criador_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao
    ADD CONSTRAINT avaliacao_criador_id_fkey FOREIGN KEY (criador_id) REFERENCES public.usuario(id);


--
-- Name: avaliacao avaliacao_disciplina_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao
    ADD CONSTRAINT avaliacao_disciplina_id_fkey FOREIGN KEY (disciplina_id) REFERENCES public.disciplina(id);


--
-- Name: avaliacao avaliacao_escola_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao
    ADD CONSTRAINT avaliacao_escola_id_fkey FOREIGN KEY (escola_id) REFERENCES public.escola(id);


--
-- Name: avaliacao avaliacao_modelo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao
    ADD CONSTRAINT avaliacao_modelo_id_fkey FOREIGN KEY (modelo_id) REFERENCES public.modelo_avaliacao(id);


--
-- Name: avaliacao_questoes avaliacao_questoes_avaliacao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao_questoes
    ADD CONSTRAINT avaliacao_questoes_avaliacao_id_fkey FOREIGN KEY (avaliacao_id) REFERENCES public.avaliacao(id);


--
-- Name: avaliacao_questoes avaliacao_questoes_questao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao_questoes
    ADD CONSTRAINT avaliacao_questoes_questao_id_fkey FOREIGN KEY (questao_id) REFERENCES public.questao(id);


--
-- Name: avaliacao avaliacao_serie_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avaliacao
    ADD CONSTRAINT avaliacao_serie_id_fkey FOREIGN KEY (serie_id) REFERENCES public.serie(id);


--
-- Name: disciplina disciplina_escola_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.disciplina
    ADD CONSTRAINT disciplina_escola_id_fkey FOREIGN KEY (escola_id) REFERENCES public.escola(id);


--
-- Name: matricula matricula_aluno_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matricula
    ADD CONSTRAINT matricula_aluno_id_fkey FOREIGN KEY (aluno_id) REFERENCES public.usuario(id);


--
-- Name: matricula matricula_ano_letivo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matricula
    ADD CONSTRAINT matricula_ano_letivo_id_fkey FOREIGN KEY (ano_letivo_id) REFERENCES public.ano_letivo(id);


--
-- Name: matricula matricula_serie_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matricula
    ADD CONSTRAINT matricula_serie_id_fkey FOREIGN KEY (serie_id) REFERENCES public.serie(id);


--
-- Name: modelo_avaliacao modelo_avaliacao_criador_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.modelo_avaliacao
    ADD CONSTRAINT modelo_avaliacao_criador_id_fkey FOREIGN KEY (criador_id) REFERENCES public.usuario(id);


--
-- Name: modelo_avaliacao modelo_avaliacao_escola_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.modelo_avaliacao
    ADD CONSTRAINT modelo_avaliacao_escola_id_fkey FOREIGN KEY (escola_id) REFERENCES public.escola(id);


--
-- Name: modelo_avaliacao modelo_avaliacao_serie_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.modelo_avaliacao
    ADD CONSTRAINT modelo_avaliacao_serie_id_fkey FOREIGN KEY (serie_id) REFERENCES public.serie(id);


--
-- Name: professor_disciplinas professor_disciplinas_disciplina_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.professor_disciplinas
    ADD CONSTRAINT professor_disciplinas_disciplina_id_fkey FOREIGN KEY (disciplina_id) REFERENCES public.disciplina(id);


--
-- Name: professor_disciplinas professor_disciplinas_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.professor_disciplinas
    ADD CONSTRAINT professor_disciplinas_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- Name: professor_series professor_series_serie_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.professor_series
    ADD CONSTRAINT professor_series_serie_id_fkey FOREIGN KEY (serie_id) REFERENCES public.serie(id);


--
-- Name: professor_series professor_series_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.professor_series
    ADD CONSTRAINT professor_series_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- Name: questao questao_criador_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questao
    ADD CONSTRAINT questao_criador_id_fkey FOREIGN KEY (criador_id) REFERENCES public.usuario(id);


--
-- Name: questao questao_disciplina_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questao
    ADD CONSTRAINT questao_disciplina_id_fkey FOREIGN KEY (disciplina_id) REFERENCES public.disciplina(id);


--
-- Name: questao questao_serie_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questao
    ADD CONSTRAINT questao_serie_id_fkey FOREIGN KEY (serie_id) REFERENCES public.serie(id);


--
-- Name: resposta resposta_questao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.resposta
    ADD CONSTRAINT resposta_questao_id_fkey FOREIGN KEY (questao_id) REFERENCES public.questao(id);


--
-- Name: resposta resposta_resultado_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.resposta
    ADD CONSTRAINT resposta_resultado_id_fkey FOREIGN KEY (resultado_id) REFERENCES public.resultado(id);


--
-- Name: resultado resultado_aluno_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.resultado
    ADD CONSTRAINT resultado_aluno_id_fkey FOREIGN KEY (aluno_id) REFERENCES public.usuario(id);


--
-- Name: resultado resultado_ano_letivo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.resultado
    ADD CONSTRAINT resultado_ano_letivo_id_fkey FOREIGN KEY (ano_letivo_id) REFERENCES public.ano_letivo(id);


--
-- Name: resultado resultado_avaliacao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.resultado
    ADD CONSTRAINT resultado_avaliacao_id_fkey FOREIGN KEY (avaliacao_id) REFERENCES public.avaliacao(id);


--
-- Name: serie_disciplinas serie_disciplinas_disciplina_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.serie_disciplinas
    ADD CONSTRAINT serie_disciplinas_disciplina_id_fkey FOREIGN KEY (disciplina_id) REFERENCES public.disciplina(id);


--
-- Name: serie_disciplinas serie_disciplinas_serie_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.serie_disciplinas
    ADD CONSTRAINT serie_disciplinas_serie_id_fkey FOREIGN KEY (serie_id) REFERENCES public.serie(id);


--
-- Name: serie serie_escola_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.serie
    ADD CONSTRAINT serie_escola_id_fkey FOREIGN KEY (escola_id) REFERENCES public.escola(id);


--
-- Name: simulado_disciplinas simulado_disciplinas_avaliacao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.simulado_disciplinas
    ADD CONSTRAINT simulado_disciplinas_avaliacao_id_fkey FOREIGN KEY (avaliacao_id) REFERENCES public.avaliacao(id);


--
-- Name: simulado_disciplinas simulado_disciplinas_disciplina_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.simulado_disciplinas
    ADD CONSTRAINT simulado_disciplinas_disciplina_id_fkey FOREIGN KEY (disciplina_id) REFERENCES public.disciplina(id);


--
-- Name: usuario usuario_escola_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_escola_id_fkey FOREIGN KEY (escola_id) REFERENCES public.escola(id);


--
-- PostgreSQL database dump complete
--

