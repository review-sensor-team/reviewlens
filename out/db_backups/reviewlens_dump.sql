--
-- PostgreSQL database dump
--

\restrict v0brCmgrlaJiDFaY2YDJ6DtAjYDh9bnwShBxO9Tmi0nXaVvXS1cSNL64CJoMzo3

-- Dumped from database version 16.11 (Debian 16.11-1.pgdg13+1)
-- Dumped by pg_dump version 16.11 (Debian 16.11-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
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
-- Name: dialogue_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dialogue_sessions (
    session_id uuid NOT NULL,
    product_no integer NOT NULL,
    category_key text,
    provider text,
    model_name text,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    ended_at timestamp with time zone,
    total_turns integer DEFAULT 0 NOT NULL,
    completed boolean DEFAULT false NOT NULL,
    exit_reason text,
    final_top_factors jsonb,
    llm_context_final jsonb,
    CONSTRAINT dialogue_sessions_exit_reason_check CHECK ((exit_reason = ANY (ARRAY['converged'::text, 'turn_limit'::text, 'user_drop'::text, 'error'::text])))
);


ALTER TABLE public.dialogue_sessions OWNER TO postgres;

--
-- Name: dialogue_turns; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dialogue_turns (
    session_id uuid NOT NULL,
    turn_index integer NOT NULL,
    question_id integer NOT NULL,
    user_message text NOT NULL,
    bot_message text,
    top_factors jsonb,
    is_final boolean DEFAULT false NOT NULL,
    llm_context jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.dialogue_turns OWNER TO postgres;

--
-- Name: llm_runs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.llm_runs (
    session_id uuid NOT NULL,
    status text NOT NULL,
    provider text,
    model_name text,
    llm_context jsonb,
    output_text text,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT llm_runs_status_check CHECK ((status = ANY (ARRAY['success'::text, 'fallback'::text, 'error'::text])))
);


ALTER TABLE public.llm_runs OWNER TO postgres;

--
-- Name: ref_factors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ref_factors (
    factor_id integer NOT NULL,
    product_no integer NOT NULL,
    factor_seq integer NOT NULL,
    factor_key text NOT NULL,
    category text NOT NULL,
    category_name text NOT NULL,
    product_name text NOT NULL,
    regret_type text,
    display_name text NOT NULL,
    description text,
    anchor_terms text,
    context_terms text,
    negation_terms text,
    weight double precision NOT NULL,
    review_mentions integer
);


ALTER TABLE public.ref_factors OWNER TO postgres;

--
-- Name: ref_products; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ref_products (
    product_no integer NOT NULL,
    product_name text NOT NULL,
    category text NOT NULL,
    category_name text NOT NULL
);


ALTER TABLE public.ref_products OWNER TO postgres;

--
-- Name: ref_questions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ref_questions (
    question_id integer NOT NULL,
    factor_id integer NOT NULL,
    factor_key text NOT NULL,
    question_text text NOT NULL,
    answer_type text NOT NULL,
    choices text,
    next_factor_hint text
);


ALTER TABLE public.ref_questions OWNER TO postgres;

--
-- Name: ref_reviews; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ref_reviews (
    product_no integer NOT NULL,
    review_id bigint NOT NULL,
    rating integer,
    text text NOT NULL,
    created_at timestamp with time zone
);


ALTER TABLE public.ref_reviews OWNER TO postgres;

--
-- Name: reference_data_versions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reference_data_versions (
    version_id integer NOT NULL,
    source_name text NOT NULL,
    description text,
    loaded_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.reference_data_versions OWNER TO postgres;

--
-- Name: reference_data_versions_version_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.reference_data_versions_version_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reference_data_versions_version_id_seq OWNER TO postgres;

--
-- Name: reference_data_versions_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.reference_data_versions_version_id_seq OWNED BY public.reference_data_versions.version_id;


--
-- Name: reference_data_versions version_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reference_data_versions ALTER COLUMN version_id SET DEFAULT nextval('public.reference_data_versions_version_id_seq'::regclass);


--
-- Data for Name: dialogue_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.dialogue_sessions (session_id, product_no, category_key, provider, model_name, started_at, ended_at, total_turns, completed, exit_reason, final_top_factors, llm_context_final) FROM stdin;
\.


--
-- Data for Name: dialogue_turns; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.dialogue_turns (session_id, turn_index, question_id, user_message, bot_message, top_factors, is_final, llm_context, created_at) FROM stdin;
\.


--
-- Data for Name: llm_runs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.llm_runs (session_id, status, provider, model_name, llm_context, output_text, error_message, created_at) FROM stdin;
\.


--
-- Data for Name: ref_factors; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ref_factors (factor_id, product_no, factor_seq, factor_key, category, category_name, product_name, regret_type, display_name, description, anchor_terms, context_terms, negation_terms, weight, review_mentions) FROM stdin;
\.


--
-- Data for Name: ref_products; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ref_products (product_no, product_name, category, category_name) FROM stdin;
\.


--
-- Data for Name: ref_questions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ref_questions (question_id, factor_id, factor_key, question_text, answer_type, choices, next_factor_hint) FROM stdin;
\.


--
-- Data for Name: ref_reviews; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ref_reviews (product_no, review_id, rating, text, created_at) FROM stdin;
\.


--
-- Data for Name: reference_data_versions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.reference_data_versions (version_id, source_name, description, loaded_at) FROM stdin;
\.


--
-- Name: reference_data_versions_version_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.reference_data_versions_version_id_seq', 1, false);


--
-- Name: dialogue_sessions dialogue_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialogue_sessions
    ADD CONSTRAINT dialogue_sessions_pkey PRIMARY KEY (session_id);


--
-- Name: dialogue_turns dialogue_turns_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialogue_turns
    ADD CONSTRAINT dialogue_turns_pkey PRIMARY KEY (session_id, turn_index);


--
-- Name: llm_runs llm_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.llm_runs
    ADD CONSTRAINT llm_runs_pkey PRIMARY KEY (session_id);


--
-- Name: ref_factors ref_factors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_factors
    ADD CONSTRAINT ref_factors_pkey PRIMARY KEY (factor_id);


--
-- Name: ref_products ref_products_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_products
    ADD CONSTRAINT ref_products_pkey PRIMARY KEY (product_no);


--
-- Name: ref_questions ref_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_questions
    ADD CONSTRAINT ref_questions_pkey PRIMARY KEY (question_id);


--
-- Name: ref_reviews ref_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_reviews
    ADD CONSTRAINT ref_reviews_pkey PRIMARY KEY (product_no, review_id);


--
-- Name: reference_data_versions reference_data_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reference_data_versions
    ADD CONSTRAINT reference_data_versions_pkey PRIMARY KEY (version_id);


--
-- Name: ref_factors uq_product_factor_seq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_factors
    ADD CONSTRAINT uq_product_factor_seq UNIQUE (product_no, factor_seq);


--
-- Name: idx_llm_status_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_llm_status_created_at ON public.llm_runs USING btree (status, created_at DESC);


--
-- Name: idx_ref_factors_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ref_factors_product ON public.ref_factors USING btree (product_no);


--
-- Name: idx_ref_questions_factor; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ref_questions_factor ON public.ref_questions USING btree (factor_id);


--
-- Name: idx_ref_reviews_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ref_reviews_product ON public.ref_reviews USING btree (product_no);


--
-- Name: idx_sessions_product_started_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sessions_product_started_at ON public.dialogue_sessions USING btree (product_no, started_at DESC);


--
-- Name: idx_sessions_started_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sessions_started_at ON public.dialogue_sessions USING btree (started_at DESC);


--
-- Name: idx_turns_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_turns_created_at ON public.dialogue_turns USING btree (created_at DESC);


--
-- Name: idx_turns_question_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_turns_question_id ON public.dialogue_turns USING btree (question_id);


--
-- Name: uq_one_final_turn_per_session; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_one_final_turn_per_session ON public.dialogue_turns USING btree (session_id) WHERE (is_final = true);


--
-- Name: dialogue_sessions dialogue_sessions_product_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialogue_sessions
    ADD CONSTRAINT dialogue_sessions_product_no_fkey FOREIGN KEY (product_no) REFERENCES public.ref_products(product_no) ON DELETE RESTRICT;


--
-- Name: dialogue_turns dialogue_turns_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialogue_turns
    ADD CONSTRAINT dialogue_turns_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.ref_questions(question_id) ON DELETE RESTRICT;


--
-- Name: dialogue_turns dialogue_turns_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialogue_turns
    ADD CONSTRAINT dialogue_turns_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.dialogue_sessions(session_id) ON DELETE CASCADE;


--
-- Name: ref_factors fk_factor_product; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_factors
    ADD CONSTRAINT fk_factor_product FOREIGN KEY (product_no) REFERENCES public.ref_products(product_no) ON DELETE CASCADE;


--
-- Name: ref_questions fk_question_factor; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_questions
    ADD CONSTRAINT fk_question_factor FOREIGN KEY (factor_id) REFERENCES public.ref_factors(factor_id) ON DELETE CASCADE;


--
-- Name: ref_reviews fk_review_product; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_reviews
    ADD CONSTRAINT fk_review_product FOREIGN KEY (product_no) REFERENCES public.ref_products(product_no) ON DELETE CASCADE;


--
-- Name: llm_runs llm_runs_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.llm_runs
    ADD CONSTRAINT llm_runs_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.dialogue_sessions(session_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict v0brCmgrlaJiDFaY2YDJ6DtAjYDh9bnwShBxO9Tmi0nXaVvXS1cSNL64CJoMzo3

