from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Dict, Optional
import numpy as np
from scipy.optimize import fsolve
import warnings
warnings.filterwarnings('ignore')

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main app without a prefix
app = FastAPI(title="Simulador de Consórcio API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class ParametrosConsorcio(BaseModel):
    valor_carta: float = 100_000
    prazo_meses: int = 120
    taxa_admin: float = 0.21
    fundo_reserva: float = 0.03
    mes_contemplacao: int = 1
    lance_livre_perc: float = 0.10
    taxa_reajuste_anual: float = 0.05

class DetalhamentoMes(BaseModel):
    mes: int
    ano: int
    fator_correcao: float
    valor_carta_corrigido: float
    parcela_corrigida: float
    lance_livre: float
    fluxo_liquido: float
    eh_contemplacao: bool

class ResumoFinanceiro(BaseModel):
    base_contrato: float
    valor_lance_livre: float
    valor_carta_contemplacao: float
    total_parcelas: float
    fluxo_contemplacao: float

class ResultadosSimulacao(BaseModel):
    cet_anual: Optional[float]
    cet_mensal: Optional[float]
    convergiu: bool
    motivo_erro: Optional[str]

class RespostaSimulacao(BaseModel):
    erro: bool
    mensagem: Optional[str] = None
    parametros: Optional[ParametrosConsorcio] = None
    resultados: Optional[ResultadosSimulacao] = None
    fluxos: List[float] = []
    detalhamento: List[DetalhamentoMes] = []
    resumo_financeiro: Optional[ResumoFinanceiro] = None

class SimuladorConsorcio:
    """Simulador de consórcio baseado na metodologia fornecida."""
    
    def __init__(self, parametros: ParametrosConsorcio):
        self.params = parametros
        self.convergiu = True
        self.motivo_erro = ""
    
    def calcular_base_lance(self) -> float:
        """Calcula base para lance: Crédito + Taxas + Fundo."""
        return self.params.valor_carta * (1 + self.params.taxa_admin + self.params.fundo_reserva)
    
    def gerar_fluxos_lance_livre(self) -> Dict:
        """Gera fluxos de caixa com metodologia corrigida."""
        try:
            # Base de cálculo
            base_contrato = self.calcular_base_lance()
            parcela_base_anual = base_contrato / (self.params.prazo_meses / 12)
            valor_lance_livre = base_contrato * self.params.lance_livre_perc
            
            fluxos = [0]  # t=0
            detalhamento = []
            
            for mes in range(1, self.params.prazo_meses + 1):
                # Correção anual (como na simulação)
                ano_atual = (mes - 1) // 12 + 1
                fator_correcao = (1 + self.params.taxa_reajuste_anual) ** (ano_atual - 1)
                
                # Valores corrigidos
                valor_carta_corrigido = self.params.valor_carta * fator_correcao
                parcela_corrigida = (parcela_base_anual / 12) * fator_correcao
                
                if mes == self.params.mes_contemplacao:
                    # Contemplação: RECEBE carta - PAGA parcela - PAGA lance livre
                    fluxo = valor_carta_corrigido - parcela_corrigida - valor_lance_livre
                else:
                    # Demais meses: apenas PAGA parcela
                    fluxo = -parcela_corrigida
                
                fluxos.append(fluxo)
                
                detalhamento.append({
                    'mes': mes,
                    'ano': ano_atual,
                    'fator_correcao': fator_correcao,
                    'valor_carta_corrigido': valor_carta_corrigido,
                    'parcela_corrigida': parcela_corrigida,
                    'lance_livre': valor_lance_livre if mes == self.params.mes_contemplacao else 0,
                    'fluxo_liquido': fluxo,
                    'eh_contemplacao': mes == self.params.mes_contemplacao
                })
            
            return {
                'fluxos': fluxos,
                'detalhamento': detalhamento,
                'resumo': {
                    'base_contrato': base_contrato,
                    'valor_lance_livre': valor_lance_livre,
                    'valor_carta_contemplacao': self.params.valor_carta * ((1 + self.params.taxa_reajuste_anual) ** ((self.params.mes_contemplacao - 1) // 12)),
                    'total_parcelas': sum(d['parcela_corrigida'] for d in detalhamento),
                    'fluxo_contemplacao': fluxos[self.params.mes_contemplacao]
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na geração de fluxos: {e}")
            return {'fluxos': [], 'detalhamento': [], 'resumo': {}}
    
    def calcular_cet(self, fluxos: List[float]) -> float:
        """Calcula CET com método robusto."""
        def vpv(taxa_mensal):
            return sum(cf / (1 + taxa_mensal) ** i for i, cf in enumerate(fluxos))
        
        if len(fluxos) < 2:
            self.convergiu = False
            self.motivo_erro = "Fluxos insuficientes"
            return np.nan
        
        # Verificar mudanças de sinal
        sinais = [np.sign(f) for f in fluxos if f != 0]
        if len(set(sinais)) < 2:
            self.convergiu = False
            self.motivo_erro = "Sem mudança de sinal nos fluxos"
            return np.nan
        
        try:
            tentativas = [0.005, 0.01, 0.015, 0.02, 0.001, 0.03, -0.001, 0.0001]
            
            for taxa_inicial in tentativas:
                try:
                    taxa_mensal = fsolve(vpv, taxa_inicial, xtol=1e-12, maxfev=2000)[0]
                    
                    if abs(vpv(taxa_mensal)) < 1e-6:
                        taxa_anual = (1 + taxa_mensal) ** 12 - 1
                        
                        if -0.99 <= taxa_anual <= 5.0:
                            self.convergiu = True
                            return taxa_anual
                
                except (ValueError, RuntimeWarning):
                    continue
            
            self.convergiu = False
            self.motivo_erro = "Convergência não alcançada"
            return np.nan
            
        except Exception as e:
            self.convergiu = False
            self.motivo_erro = f"Erro matemático: {str(e)[:50]}"
            return np.nan
    
    def simular_cenario_completo(self) -> Dict:
        """Simulação completa do cenário atual."""
        resultado_fluxos = self.gerar_fluxos_lance_livre()
        
        if not resultado_fluxos['fluxos']:
            return {
                'erro': True,
                'mensagem': 'Erro na geração de fluxos'
            }
        
        cet = self.calcular_cet(resultado_fluxos['fluxos'])
        
        return {
            'erro': False,
            'parametros': self.params.dict(),
            'resultados': {
                'cet_anual': cet,
                'cet_mensal': (1 + cet) ** (1/12) - 1 if not np.isnan(cet) else np.nan,
                'convergiu': self.convergiu,
                'motivo_erro': self.motivo_erro
            },
            'fluxos': resultado_fluxos['fluxos'],
            'detalhamento': resultado_fluxos['detalhamento'],
            'resumo_financeiro': resultado_fluxos['resumo']
        }

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Simulador de Consórcio API - Ativo"}

@api_router.post("/simular", response_model=RespostaSimulacao)
async def simular_consorcio(parametros: ParametrosConsorcio):
    """Simula um consórcio com os parâmetros fornecidos."""
    try:
        # Validações básicas
        if parametros.valor_carta <= 0:
            raise HTTPException(status_code=400, detail="Valor da carta deve ser positivo")
        
        if parametros.prazo_meses <= 0:
            raise HTTPException(status_code=400, detail="Prazo deve ser positivo")
        
        if parametros.mes_contemplacao > parametros.prazo_meses:
            raise HTTPException(status_code=400, detail="Mês de contemplação não pode ser maior que o prazo")
        
        if parametros.mes_contemplacao <= 0:
            raise HTTPException(status_code=400, detail="Mês de contemplação deve ser positivo")
        
        # Criar simulador e executar
        simulador = SimuladorConsorcio(parametros)
        resultado = simulador.simular_cenario_completo()
        
        if resultado['erro']:
            return RespostaSimulacao(
                erro=True,
                mensagem=resultado.get('mensagem', 'Erro desconhecido na simulação')
            )
        
        # Converter detalhamento para o modelo Pydantic
        detalhamento_convertido = []
        for item in resultado['detalhamento']:
            detalhamento_convertido.append(DetalhamentoMes(**item))
        
        return RespostaSimulacao(
            erro=False,
            parametros=ParametrosConsorcio(**resultado['parametros']),
            resultados=ResultadosSimulacao(**resultado['resultados']),
            fluxos=resultado['fluxos'],
            detalhamento=detalhamento_convertido,
            resumo_financeiro=ResumoFinanceiro(**resultado['resumo_financeiro'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na simulação: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@api_router.get("/parametros-padrao", response_model=ParametrosConsorcio)
async def get_parametros_padrao():
    """Retorna os parâmetros padrão para simulação."""
    return ParametrosConsorcio()

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)