# -*- coding: utf-8 -*-
"""DTOs OpenAPI por passo do simulador (paridade com Streamlit)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SessionCreateIn(BaseModel):
    email: Optional[str] = None


class SessionPatchIn(BaseModel):
    passo_simulacao: Optional[str] = None
    dados_cliente: Optional[Dict[str, Any]] = None
    cliente_ativo: Optional[bool] = None
    session_ui: Optional[Dict[str, Any]] = None
    unidade_selecionada: Optional[Dict[str, Any]] = None
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    user_imobiliaria: Optional[str] = None
    user_cargo: Optional[str] = None


class EstadoSessaoOut(BaseModel):
    email: Optional[str] = None
    passo_simulacao: str = "input"
    dados_cliente: Dict[str, Any] = Field(default_factory=dict)
    cliente_ativo: bool = False
    session_ui: Dict[str, Any] = Field(default_factory=dict)
    unidade_selecionada: Optional[Dict[str, Any]] = None
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    user_imobiliaria: Optional[str] = None
    user_cargo: Optional[str] = None


class SessionCreatedOut(BaseModel):
    session_id: str
    estado: EstadoSessaoOut


class ClienteAtivarCpfIn(BaseModel):
    """Ativa sessão a partir de BD Clientes + última linha em BD Simulações (mesmo CPF)."""
    cpf: str = Field(..., min_length=3, description="CPF com ou sem máscara")


class ClienteIn(BaseModel):
    nome: Optional[str] = None
    cpf: Optional[str] = None
    renda: Optional[float] = None
    politica: Optional[str] = "Direcional"
    ranking: Optional[str] = "DIAMANTE"
    social: Optional[bool] = False
    cotista: Optional[bool] = False
    fgts: Optional[float] = None
    # campos adicionais livres
    extra: Optional[Dict[str, Any]] = None


class ClienteConfirmarIn(BaseModel):
    """Espelha o form `form_cadastro` do Streamlit (etapa input)."""

    nome: str
    cpf: str
    data_nascimento: Optional[str] = None
    qtd_participantes: int = Field(1, ge=1, le=4)
    rendas_lista: List[float] = Field(default_factory=list)
    ranking: str = "DIAMANTE"
    politica: str = "Direcional"
    social: bool = False
    cotista: bool = True


class PassoTransicaoIn(BaseModel):
    """Avançar para o passo indicado (validação opcional no router)."""

    passo: str


class PagamentoEstadoIn(BaseModel):
    """Atualização completa do ecrã payment_flow."""

    ps_usado: Optional[float] = None
    ps_parcelas: Optional[int] = None
    ato_final: Optional[float] = None
    ato_30: Optional[float] = None
    ato_60: Optional[float] = None
    ato_90: Optional[float] = None
    volta_caixa: Optional[float] = None


class DistribuirAtosIn(BaseModel):
    n_parcelas: int = Field(..., ge=2, le=3, description="2 = 30/60, 3 = 30/60/90")


class FechamentoIn(BaseModel):
    finan_usado: Optional[float] = None
    fgts_sub_usado: Optional[float] = None
    ps_usado: Optional[float] = None
    ps_mensal: Optional[float] = None
    ps_parcelas: Optional[int] = None
    parcela_financiamento: Optional[float] = None
    prazo_financiamento: Optional[int] = None
    sistema_amortizacao: Optional[str] = None
    valor_avaliacao_curva: Optional[float] = None


class RecomendacoesIn(BaseModel):
    empreendimento: Optional[str] = None


class UnidadeSelecionarIn(BaseModel):
    identificador: str = Field(..., description="Identificador da unidade no estoque")


class EstoqueQueryParams(BaseModel):
    bairro: Optional[List[str]] = None
    empreendimento: Optional[List[str]] = None
    cobertura_min_pct: float = 0.0
    ordem: str = "menor_preco"
    preco_max: Optional[float] = None


class PagamentoSimIn(BaseModel):
    valor_financiado: float = Field(..., ge=0)
    meses_fin: int = Field(..., ge=1)
    taxa_anual: float = Field(..., ge=0)
    sistema: str = "SAC"
    ps_mensal: float = 0.0
    meses_ps: int = 0
    ato_final: float = 0.0
    ato_30: float = 0.0
    ato_60: float = 0.0
    ato_90: float = 0.0


class ResumoOut(BaseModel):
    dados_cliente: Dict[str, Any]
    unidade_selecionada: Optional[Dict[str, Any]]
    passo_simulacao: str


class SalvarSimulacaoOut(BaseModel):
    ok: bool
    message: str
    reset_sessao: bool = False


class PdfRequest(BaseModel):
    dados: Optional[Dict[str, Any]] = None


class EmailRequest(BaseModel):
    destinatario: str
    nome_cliente: str
    tipo: str = "cliente"
    dados: Optional[Dict[str, Any]] = None


class HistoricoImportIn(BaseModel):
    """Uma linha de BD Simulações (como devolvida por `/api/cadastros/buscar`)."""

    row: Dict[str, Any] = Field(..., description="Registo completo da planilha")
