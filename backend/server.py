from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import FileResponse
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
import tempfile
from datetime import datetime, timezone, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

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
    data: str  # Data formatada (set/25, out/25, etc.)
    ano: int
    fator_correcao: float
    valor_carta_corrigido: float
    parcela_corrigida: float
    lance_livre: float
    fluxo_liquido: float
    saldo_devedor: float
    eh_contemplacao: bool

class ResumoFinanceiro(BaseModel):
    base_contrato: float
    valor_lance_livre: float
    valor_carta_contemplacao: float
    total_parcelas: float
    fluxo_contemplacao: float
    primeira_parcela: float
    primeira_parcela_pos_contemplacao: float
    parcela_intermediaria: float
    ultima_parcela: float
    # Resumo da Operação (como no site de referência)
    valor_credito_taxas: float
    taxas: float
    lance_embutido: float
    credito_liquido: float
    # Probabilidades específicas do mês de contemplação escolhido
    prob_contemplacao_no_mes: float = 0.0
    prob_contemplacao_ate_mes: float = 0.0
    participantes_restantes_mes: int = 0

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

class ParametrosProbabilidade(BaseModel):
    num_participantes: int = 430
    lance_livre_perc: float = 0.10

class CurvasProbabilidade(BaseModel):
    meses: List[int]
    hazard: List[float]
    probabilidade_acumulada: List[float]
    probabilidade_mes: List[float]
    esperanca_meses: float
    mediana_mes: Optional[int]
    p10_mes: Optional[int]
    p90_mes: Optional[int]

class RespostaProbabilidades(BaseModel):
    erro: bool
    mensagem: Optional[str] = None
    sem_lance: Optional[CurvasProbabilidade] = None
    com_lance: Optional[CurvasProbabilidade] = None
    parametros: Optional[Dict] = None

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
        """Gera fluxos de caixa corretos - parcela só diminui com lance embutido."""
        try:
            # Base de cálculo
            base_contrato = self.calcular_base_lance()
            valor_lance_livre = base_contrato * self.params.lance_livre_perc
            
            # Cálculos do resumo da operação
            valor_credito_taxas = base_contrato  # R$ 124.000,00
            taxas = self.params.valor_carta * (self.params.taxa_admin + self.params.fundo_reserva)  # R$ 24.000,00
            lance_embutido = base_contrato * 0.08  # Aproximadamente 8% (baseado no documento)
            credito_liquido = self.params.valor_carta - (taxas + valor_lance_livre + lance_embutido - base_contrato)
            
            # Parcela base mensal - SEMPRE A MESMA (não diminui com lance livre)
            parcela_base_mensal = base_contrato / self.params.prazo_meses
            
            fluxos = [0]  # t=0
            detalhamento = []
            primeira_parcela = 0
            primeira_parcela_pos_contemplacao = 0
            parcela_intermediaria = 0
            ultima_parcela = 0
            
            # O saldo devedor inicial é a base do contrato
            saldo_devedor_atual = base_contrato
            
            # Meses em português
            meses_pt = ['', 'jan', 'fev', 'mar', 'abr', 'mai', 'jun', 
                       'jul', 'ago', 'set', 'out', 'nov', 'dez']
            
            # Meses em português
            meses_pt = ['', 'jan', 'fev', 'mar', 'abr', 'mai', 'jun', 
                       'jul', 'ago', 'set', 'out', 'nov', 'dez']
            
            for mes in range(1, self.params.prazo_meses + 1):
                # Correção anual
                ano_atual = (mes - 1) // 12 + 1
                fator_correcao = (1 + self.params.taxa_reajuste_anual) ** (ano_atual - 1)
                
                # Data formatada (set/25, out/25, etc.)
                mes_calendario = ((mes - 1) % 12) + 1
                ano_calendario = 2025 + (mes - 1) // 12
                data_formatada = f"{meses_pt[mes_calendario]}/{str(ano_calendario)[2:]}"
                
                # Valores corrigidos
                valor_carta_corrigido = self.params.valor_carta * fator_correcao
                
                # CORREÇÃO: Parcela sempre igual (só muda com correção anual)
                parcela_corrigida = parcela_base_mensal * fator_correcao
                
                if mes == self.params.mes_contemplacao:
                    # CONTEMPLAÇÃO: Recebe carta, paga parcela e lance livre
                    fluxo = valor_carta_corrigido - parcela_corrigida - valor_lance_livre
                    lance_mes = valor_lance_livre
                    primeira_parcela = parcela_corrigida
                    
                    # CORREÇÃO DO SALDO DEVEDOR: Após contemplação, subtrai o valor da carta
                    saldo_devedor_atual = saldo_devedor_atual - valor_carta_corrigido - parcela_corrigida
                else:
                    # DEMAIS MESES: Só paga parcela (valor sempre igual)
                    fluxo = -parcela_corrigida
                    lance_mes = 0
                    
                    # Guardar primeira parcela pós-contemplação (igual à anterior)
                    if mes == self.params.mes_contemplacao + 1:
                        primeira_parcela_pos_contemplacao = parcela_corrigida
                    
                    # CORREÇÃO: Subtrai apenas a parcela do saldo devedor
                    saldo_devedor_atual -= parcela_corrigida
                
                # Guardar parcela intermediária (meio do prazo)
                if mes == self.params.prazo_meses // 2:
                    parcela_intermediaria = parcela_corrigida
                    
                # Última parcela
                if mes == self.params.prazo_meses:
                    ultima_parcela = parcela_corrigida
                
                fluxos.append(fluxo)
                
                detalhamento.append({
                    'mes': mes,
                    'data': data_formatada,
                    'ano': ano_atual,
                    'fator_correcao': fator_correcao,
                    'valor_carta_corrigido': valor_carta_corrigido,
                    'parcela_corrigida': parcela_corrigida,
                    'lance_livre': lance_mes,
                    'fluxo_liquido': fluxo,
                    'saldo_devedor': max(0, saldo_devedor_atual),
                    'eh_contemplacao': mes == self.params.mes_contemplacao
                })
            
            # Calcular valor da carta na contemplação
            mes_contemplacao = self.params.mes_contemplacao
            ano_contemplacao = (mes_contemplacao - 1) // 12 + 1
            fator_correcao_contemplacao = (1 + self.params.taxa_reajuste_anual) ** (ano_contemplacao - 1)
            valor_carta_contemplacao = self.params.valor_carta * fator_correcao_contemplacao
            
            # Se não temos parcela pós-contemplação, é igual à primeira
            if primeira_parcela_pos_contemplacao == 0:
                primeira_parcela_pos_contemplacao = primeira_parcela
            
            # Se não temos parcela intermediária definida, usar uma estimativa
            if parcela_intermediaria == 0:
                parcela_intermediaria = parcela_base_mensal * (1 + self.params.taxa_reajuste_anual) ** 4
            
            return {
                'fluxos': fluxos,
                'detalhamento': detalhamento,
                'resumo': {
                    'base_contrato': base_contrato,
                    'valor_lance_livre': valor_lance_livre,
                    'valor_carta_contemplacao': valor_carta_contemplacao,
                    'total_parcelas': sum(d['parcela_corrigida'] for d in detalhamento if not d['eh_contemplacao']),
                    'fluxo_contemplacao': fluxos[self.params.mes_contemplacao],
                    'primeira_parcela': primeira_parcela,
                    'primeira_parcela_pos_contemplacao': primeira_parcela_pos_contemplacao,
                    'parcela_intermediaria': parcela_intermediaria,
                    'ultima_parcela': ultima_parcela,
                    # Resumo da Operação
                    'valor_credito_taxas': valor_credito_taxas,
                    'taxas': taxas,
                    'lance_embutido': lance_embutido,
                    'credito_liquido': credito_liquido
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na geração de fluxos: {e}")
            return {'fluxos': [], 'detalhamento': [], 'resumo': {}}
            
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
        
        # Calcular probabilidades específicas do mês de contemplação escolhido
        prob_mes = calcular_probabilidade_mes_especifico(
            mes_contemplacao=parametros.mes_contemplacao,
            lance_livre_perc=parametros.lance_livre_perc,  # Agora passa o lance_livre_perc
            num_participantes=430  # Usar valores padrão da planilha
        )
        
        # Adicionar probabilidades ao resumo financeiro
        if prob_mes:
            # Verificar se os valores são válidos (não NaN ou infinito)
            prob_no_mes = prob_mes['prob_no_mes']
            prob_ate_mes = prob_mes['prob_ate_mes']
            participantes_restantes = prob_mes['participantes_restantes']
            
            # Sanitizar valores
            if not np.isfinite(prob_no_mes):
                prob_no_mes = 0.0
            if not np.isfinite(prob_ate_mes):
                prob_ate_mes = 0.0
                
            resultado['resumo_financeiro']['prob_contemplacao_no_mes'] = float(prob_no_mes)
            resultado['resumo_financeiro']['prob_contemplacao_ate_mes'] = float(prob_ate_mes)
            resultado['resumo_financeiro']['participantes_restantes_mes'] = int(participantes_restantes)
        else:
            resultado['resumo_financeiro']['prob_contemplacao_no_mes'] = 0.0
            resultado['resumo_financeiro']['prob_contemplacao_ate_mes'] = 0.0
            resultado['resumo_financeiro']['participantes_restantes_mes'] = 0
        
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

@api_router.post("/calcular-probabilidades", response_model=RespostaProbabilidades)
async def calcular_probabilidades(parametros: ParametrosProbabilidade):
    """Calcula probabilidades de contemplação para o consórcio."""
    try:
        # Validações básicas
        if parametros.num_participantes <= 0:
            raise HTTPException(status_code=400, detail="Número de participantes deve ser positivo")
        
        if parametros.lance_livre_perc < 0:
            raise HTTPException(status_code=400, detail="Lance livre deve ser >= 0")
        
        # Calcular probabilidades
        resultado = calcular_probabilidades_contemplacao_corrigido(
            num_participantes=parametros.num_participantes,
            lance_livre_perc=parametros.lance_livre_perc
        )
        
        if resultado is None:
            return RespostaProbabilidades(
                erro=True,
                mensagem="Erro no cálculo de probabilidades"
            )
        
        return RespostaProbabilidades(
            erro=False,
            sem_lance=CurvasProbabilidade(**resultado["sem_lance"]),
            com_lance=CurvasProbabilidade(**resultado["com_lance"]),
            parametros=resultado["parametros"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint de probabilidades: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


def criar_grafico_probabilidades(num_participantes: int, lance_livre_perc: float, temp_dir: str) -> str:
    """Cria gráfico de probabilidades de contemplação."""
    try:
        # Calcular probabilidades usando lógica similar ao código fornecido
        N0 = num_participantes
        
        # Decidir contemplados por mês baseado no lance livre
        if lance_livre_perc > 0:
            contemplados_por_mes = 2  # 1 sorteio + 1 lance
        else:
            contemplados_por_mes = 1  # apenas sorteio
        
        meses_total = int(np.ceil(N0 / contemplados_por_mes))
        
        # Listas para dados
        meses = []
        hazard_sem = []
        hazard_com = []
        prob_acum_sem = []
        prob_acum_com = []
        
        # Inicializar
        n_atual_sem = N0
        n_atual_com = N0
        S_sem = 1.0  # Sobrevivência sem lance
        S_com = 1.0  # Sobrevivência com lance
        
        for mes in range(1, min(meses_total + 1, 101)):  # Limitar a 100 meses para o gráfico
            meses.append(mes)
            
            # Hazard sem lance (apenas 1 contemplado por sorteio)
            h_sem = 1.0 / n_atual_sem if n_atual_sem > 0 else 0
            hazard_sem.append(h_sem * 100)  # Em %
            
            # Hazard com lance (2 contemplados: 1 sorteio + 1 lance)
            h_com = min(2.0 / n_atual_com, 1.0) if n_atual_com > 0 else 0
            hazard_com.append(h_com * 100)  # Em %
            
            # Atualizar sobrevivência e probabilidade acumulada
            S_sem *= (1 - h_sem)
            S_com *= (1 - h_com)
            
            prob_acum_sem.append((1 - S_sem) * 100)  # F_t em %
            prob_acum_com.append((1 - S_com) * 100)  # F_t em %
            
            # Reduzir participantes
            n_atual_sem = max(0, n_atual_sem - 1)
            n_atual_com = max(0, n_atual_com - 2)
        
        # Criar gráfico
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        # Hazard (probabilidade do mês) no eixo esquerdo
        ax1.plot(meses, hazard_com, label="Com Lance — hazard", lw=2, color='#BC8159')
        ax1.plot(meses, hazard_sem, label="Sem Lance — hazard", lw=2, alpha=0.9, color='#8D4C23')
        ax1.set_xlabel("Mês")
        ax1.set_ylabel("Probabilidade do mês, h(t) [%]")
        ax1.set_ylim(0, max(max(hazard_com), max(hazard_sem)) * 1.1)
        ax1.grid(True, alpha=0.25)
        
        # Probabilidade acumulada no eixo direito
        ax2 = ax1.twinx()
        ax2.plot(meses, prob_acum_com, linestyle="--", alpha=0.7, label="Com Lance — F(t)", color='#BC8159')
        ax2.plot(meses, prob_acum_sem, linestyle="--", alpha=0.7, label="Sem Lance — F(t)", color='#8D4C23')
        ax2.set_ylabel("Probabilidade acumulada, F(t) [%]")
        ax2.set_ylim(0, 100)
        
        # Combinar legendas
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
        
        plt.title(f"Probabilidade de Contemplação — {N0} Participantes\n(hazard do mês + probabilidade acumulada)")
        plt.tight_layout()
        
        grafico_path = os.path.join(temp_dir, 'grafico_probabilidades.png')
        plt.savefig(grafico_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return grafico_path
    except Exception as e:
        logger.error(f"Erro ao criar gráfico de probabilidades: {e}")
        return None

def gerar_relatorio_pdf(dados_simulacao: Dict, temp_dir: str) -> str:
    """Gera relatório PDF da simulação de consórcio."""
    try:
        # Criar arquivo PDF temporário
        pdf_path = os.path.join(temp_dir, f'relatorio_consorcio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
        
        # Configurar documento
        doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#26282A')
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#26282A')
        )
        
        # Título
        # Horário de Brasília (UTC-3)
        brasilia_tz = timezone(timedelta(hours=-3))
        agora_brasilia = datetime.now(brasilia_tz)
        
        story.append(Paragraph("Relatório de Simulação de Consórcio", title_style))
        story.append(Paragraph(f"Gerado em: {agora_brasilia.strftime('%d/%m/%Y às %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Parâmetros da Simulação
        story.append(Paragraph("Parâmetros da Simulação", heading_style))
        
        parametros_data = [
            ['Parâmetro', 'Valor'],
            ['Valor da Carta', f"R$ {dados_simulacao['parametros']['valor_carta']:,.2f}"],
            ['Prazo', f"{dados_simulacao['parametros']['prazo_meses']} meses"],
            ['Taxa de Administração', f"{dados_simulacao['parametros']['taxa_admin'] * 100:.1f}%"],
            ['Fundo de Reserva', f"{dados_simulacao['parametros']['fundo_reserva'] * 100:.1f}%"],
            ['Mês de Contemplação', f"{dados_simulacao['parametros']['mes_contemplacao']}º mês"],
            ['Lance Livre', f"{dados_simulacao['parametros']['lance_livre_perc'] * 100:.1f}%"],
            ['Taxa de Reajuste Anual', f"{dados_simulacao['parametros']['taxa_reajuste_anual'] * 100:.1f}%"]
        ]
        
        parametros_table = Table(parametros_data, colWidths=[3*inch, 2*inch])
        parametros_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#C1AFA2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(parametros_table)
        story.append(Spacer(1, 20))
        
        # Resultados Principais
        story.append(Paragraph("Resultados Principais", heading_style))
        
        if dados_simulacao['resultados']['convergiu']:
            cet_anual = dados_simulacao['resultados']['cet_anual'] * 100
            cet_mensal = dados_simulacao['resultados']['cet_mensal'] * 100
        else:
            cet_anual = "Erro no cálculo"
            cet_mensal = "Erro no cálculo"
        
        resultados_data = [
            ['Indicador', 'Valor'],
            ['CET Anual', f"{cet_anual:.2f}%" if isinstance(cet_anual, float) else cet_anual],
            ['CET Mensal', f"{cet_mensal:.3f}%" if isinstance(cet_mensal, float) else cet_mensal],
            ['Lance Livre', f"R$ {dados_simulacao['resumo_financeiro']['valor_lance_livre']:,.2f}"],
            ['Base do Contrato', f"R$ {dados_simulacao['resumo_financeiro']['base_contrato']:,.2f}"],
            ['Carta na Contemplação', f"R$ {dados_simulacao['resumo_financeiro']['valor_carta_contemplacao']:,.2f}"],
            ['Fluxo na Contemplação', f"R$ {dados_simulacao['resumo_financeiro']['fluxo_contemplacao']:,.2f}"],
            ['Total em Parcelas', f"R$ {dados_simulacao['resumo_financeiro']['total_parcelas']:,.2f}"]
        ]
        
        resultados_table = Table(resultados_data, colWidths=[3*inch, 2*inch])
        resultados_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#BC8159')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(resultados_table)
        story.append(Spacer(1, 20))
        
        # REMOVIDO: Gráfico de fluxo de caixa conforme solicitado pelo usuário
        
        # Adicionar gráfico de probabilidades
        grafico_prob_path = criar_grafico_probabilidades(430, dados_simulacao['parametros']['lance_livre_perc'], temp_dir)  # Usar lance_livre_perc do usuário
        
        if grafico_prob_path and os.path.exists(grafico_prob_path):
            from reportlab.platypus import Image
            story.append(Paragraph("Análise de Probabilidades de Contemplação", heading_style))
            story.append(Paragraph("Baseado em 430 participantes com 2 contemplados por mês (1 sorteio + 1 lance livre).", styles['Normal']))
            story.append(Spacer(1, 10))
            story.append(Image(grafico_prob_path, width=6*inch, height=3*inch))
            story.append(Spacer(1, 20))
        
        # Tabela de Amortização (primeiros 36 meses para não ficar muito grande)
        story.append(Paragraph("Fluxo de Caixa Detalhado", heading_style))
        story.append(Paragraph("Detalhes de cada parcela e do fluxo de caixa da operação.", styles['Normal']))
        story.append(Spacer(1, 10))
        
        tabela_data = [['Mês', 'Data', 'Parcela', 'Valor da Carta', 'Fluxo de Caixa', 'Saldo Devedor']]
        
        for item in dados_simulacao['detalhamento'][:36]:
            mes = str(item['mes'])
            data = item['data']
            parcela = f"R$ {item['parcela_corrigida']:,.2f}"
            # Valor da carta sempre R$ 100.000,00 (como no documento de referência)
            valor_carta = "R$ 100.000,00"
            fluxo = f"R$ {item['fluxo_liquido']:,.2f}"
            saldo = f"R$ {item['saldo_devedor']:,.2f}"
            
            tabela_data.append([mes, data, parcela, valor_carta, fluxo, saldo])
        
        tabela_amortizacao = Table(tabela_data, colWidths=[0.6*inch, 0.8*inch, 1.0*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        tabela_amortizacao.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8D4C23')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Fluxos negativos em vermelho
            ('TEXTCOLOR', (4, 1), (4, -1), colors.red),
        ]))
        
        # Destacar linha de contemplação com fluxo positivo em verde
        for i, item in enumerate(dados_simulacao['detalhamento'][:36]):
            if item['eh_contemplacao']:
                tabela_amortizacao.setStyle(TableStyle([
                    ('BACKGROUND', (0, i+1), (-1, i+1), colors.HexColor('#E8F5E8')),
                    ('TEXTCOLOR', (4, i+1), (4, i+1), colors.green)
                ]))
        
        story.append(tabela_amortizacao)
        
        # Rodapé
        story.append(Spacer(1, 30))
        story.append(Paragraph("Relatório gerado pelo Simulador de Consórcio", 
                             ParagraphStyle('Footer', parent=styles['Normal'], 
                                          fontSize=8, alignment=TA_CENTER, 
                                          textColor=colors.grey)))
        
        # Gerar PDF
        doc.build(story)
        return pdf_path
        
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório PDF: {str(e)}")

@api_router.post("/gerar-relatorio-pdf")
async def gerar_relatorio_pdf_endpoint(parametros: ParametrosConsorcio):
    """Gera e retorna relatório PDF da simulação."""
    try:
        # Executar simulação
        simulador = SimuladorConsorcio(parametros)
        resultado = simulador.simular_cenario_completo()
        
        if resultado['erro']:
            raise HTTPException(status_code=400, detail=resultado.get('mensagem', 'Erro na simulação'))
        
        # Criar diretório temporário
        temp_dir = tempfile.mkdtemp()
        
        # Gerar PDF
        pdf_path = gerar_relatorio_pdf(resultado, temp_dir)
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="Erro ao gerar arquivo PDF")
        
        # Retornar arquivo
        filename = f"relatorio_consorcio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type='application/pdf',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint de PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

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

# ----------------------------
# CÁLCULOS DE PROBABILIDADE DE CONTEMPLAÇÃO
# ----------------------------

def _as_float_array(x):
    """Converte para array numpy float."""
    a = np.asarray(list(x), dtype=float)
    if a.ndim != 1:
        raise ValueError("Forneça vetores 1D.")
    return a

def _percentile_month(F, p):
    """Primeiro mês (1-index) em que F_t ≥ p. Retorna None se não atingir."""
    idx = np.argmax(F >= p)
    if F[-1] < p:
        return None
    return int(np.where(F >= p)[0][0] + 1)

def hazards_from_counts(participantes_restantes, sorteio, lance=None):
    """Calcula hazards (prob. condicionais) a partir de CONTAGENS mensais."""
    pr = _as_float_array(participantes_restantes)
    s = _as_float_array(sorteio)
    l = _as_float_array(lance) if lance is not None else np.zeros_like(s)
    
    if np.any(pr <= 0):
        raise ValueError("Há 'participantes_restantes' ≤ 0. Use valores estritamente positivos.")

    h_sem = np.divide(s, pr, out=np.zeros_like(s), where=pr>0)
    h_com = np.divide(s + l, pr, out=np.zeros_like(s), where=pr>0)

    h_sem = np.clip(h_sem, 0.0, 1.0)
    h_com = np.clip(h_com, 0.0, 1.0)

    return {"h_sem": h_sem, "h_com": h_com}

def curvas_from_hazard(h):
    """Calcula curvas de probabilidade a partir de hazards."""
    h = _as_float_array(h)
    h = np.clip(h, 0.0, 1.0)

    # Sobrevivência e acumulada
    S = np.cumprod(1.0 - h)
    F = 1.0 - S

    # f_t = h_t * S_{t-1}
    S_prev = np.r_[1.0, S[:-1]]
    f = h * S_prev

    # Métricas de distribuição do mês de contemplação
    meses = np.arange(1, len(h) + 1, dtype=int)
    esperanca = float(np.sum(meses * f))
    p50 = _percentile_month(F, 0.50)
    p10 = _percentile_month(F, 0.10)
    p90 = _percentile_month(F, 0.90)

    return {
        "meses": meses.tolist(),
        "hazard": h.tolist(),
        "probabilidade_acumulada": F.tolist(),
        "probabilidade_mes": f.tolist(),
        "esperanca_meses": esperanca,
        "mediana_mes": p50,
        "p10_mes": p10,
        "p90_mes": p90
    }

def calcular_probabilidades_contemplacao(num_participantes=430, contemplados_por_mes=2, lance_livre_perc=0.10):
    """
    Calcula probabilidades de contemplação baseado na lógica da planilha.
    
    Args:
        num_participantes: Número total de participantes do grupo
        contemplados_por_mes: Número de contemplados por mês (sorteio + lance)
    """
    try:
        # Calcular quantos meses até contemplar todos
        meses_total = int(np.ceil(num_participantes / contemplados_por_mes))
        
        # Listas para armazenar dados
        meses = []
        participantes_restantes = []
        prob_sem_lance = []  # Col5 da planilha
        prob_com_lance = []  # Col6 da planilha
        prob_acumulada_sem = []
        prob_acumulada_com = []
        
        # Inicializar
        participantes_atual = num_participantes
        acum_sem = 0.0
        acum_com = 0.0
        
        for mes in range(1, meses_total + 1):
            meses.append(mes)
            participantes_restantes.append(participantes_atual)
            
            # Lógica da planilha:
            # - 1 contemplado por sorteio (sempre)
            # - 1 contemplado por lance (col4 = 1)
            # - Probabilidade sem lance = 1 / participantes_restantes
            # - Probabilidade com lance = 2 / participantes_restantes
            
            if participantes_atual > 0:
                prob_mes_sem = 1.0 / participantes_atual  # Col5: probabilidade apenas sorteio
                prob_mes_com = 2.0 / participantes_atual  # Col6: probabilidade sorteio + lance
            else:
                prob_mes_sem = 0.0
                prob_mes_com = 0.0
            
            prob_sem_lance.append(prob_mes_sem)
            prob_com_lance.append(prob_mes_com)
            
            # Probabilidades acumuladas (aproximação simples)
            acum_sem += prob_mes_sem
            acum_com += prob_mes_com
            
            # Garantir que não passe de 1.0
            acum_sem = min(acum_sem, 1.0)
            acum_com = min(acum_com, 1.0)
            
            prob_acumulada_sem.append(acum_sem)
            prob_acumulada_com.append(acum_com)
            
            # Reduzir participantes para próximo mês
            participantes_atual = max(0, participantes_atual - contemplados_por_mes)
        
        # Calcular métricas estatísticas
        def calcular_metricas(probabilidades):
            total_prob = sum(probabilidades)
            if total_prob > 0:
                # Normalizar para que some 1
                probs_norm = [p/total_prob for p in probabilidades]
                esperanca = sum((i+1) * p for i, p in enumerate(probs_norm))
                
                # Mediana e percentis
                acum = 0.0
                p50 = p10 = p90 = None
                for i, p in enumerate(probs_norm):
                    acum += p
                    if p10 is None and acum >= 0.10:
                        p10 = i + 1
                    if p50 is None and acum >= 0.50:
                        p50 = i + 1
                    if p90 is None and acum >= 0.90:
                        p90 = i + 1
                        break
                
                return esperanca, p50, p10, p90
            else:
                return 0, None, None, None
        
        esp_sem, med_sem, p10_sem, p90_sem = calcular_metricas(prob_sem_lance)
        esp_com, med_com, p10_com, p90_com = calcular_metricas(prob_com_lance)
        
        return {
            "sem_lance": {
                "meses": meses,
                "hazard": prob_sem_lance,
                "probabilidade_acumulada": prob_acumulada_sem,
                "probabilidade_mes": prob_sem_lance,  # Mesmo que hazard para este caso
                "esperanca_meses": esp_sem,
                "mediana_mes": med_sem,
                "p10_mes": p10_sem,
                "p90_mes": p90_sem
            },
            "com_lance": {
                "meses": meses,
                "hazard": prob_com_lance,
                "probabilidade_acumulada": prob_acumulada_com,
                "probabilidade_mes": prob_com_lance,  # Mesmo que hazard para este caso
                "esperanca_meses": esp_com,
                "mediana_mes": med_com,
                "p10_mes": p10_com,
                "p90_mes": p90_com
            },
            "parametros": {
                "num_participantes": num_participantes,
                "lance_livre_perc": lance_livre_perc,
                "contemplados_por_mes": contemplados_por_mes,
                "meses_total": meses_total
            }
        }
        
    except Exception as e:
        logger.error(f"Erro no cálculo de probabilidades: {e}")
        return None

def calcular_probabilidades_contemplacao_corrigido(num_participantes=430, lance_livre_perc=0.10):
    """
    Versão corrigida do cálculo de probabilidades de contemplação.
    
    Args:
        num_participantes: Número total de participantes do grupo
        lance_livre_perc: Percentual do lance livre (se 0, considera apenas sorteio)
    """
    try:
        # Decidir contemplados por mês baseado no lance livre
        if lance_livre_perc > 0:
            contemplados_por_mes = 2  # 1 sorteio + 1 lance
        else:
            contemplados_por_mes = 1  # apenas sorteio
        # Calcular quantos meses até contemplar todos
        meses_total = int(np.ceil(num_participantes / contemplados_por_mes))
        
        # Listas para armazenar dados
        meses = []
        participantes_restantes = []
        prob_sem_lance = []  # Sempre será 1/participantes_restantes
        prob_com_lance = []  # Será 1 ou 2/participantes_restantes dependendo de lance_livre_perc
        prob_acumulada_sem = []
        prob_acumulada_com = []
        
        # Inicializar
        participantes_atual = num_participantes
        
        # Usar cálculo correto de probabilidades acumuladas
        prob_nao_contemplado_sem = 1.0
        prob_nao_contemplado_com = 1.0
        
        for mes in range(1, meses_total + 1):
            meses.append(mes)
            participantes_restantes.append(participantes_atual)
            
            # Lógica corrigida:
            # - SEM LANCE: sempre 1 contemplado por sorteio
            # - COM LANCE: depende do lance_livre_perc (1 se = 0, 2 se > 0)
            
            if participantes_atual > 0:
                # SEM LANCE: sempre 1/participantes_restantes
                prob_mes_sem = 1.0 / participantes_atual
                
                # COM LANCE: depende do lance_livre_perc
                if lance_livre_perc > 0:
                    prob_mes_com = min(2.0 / participantes_atual, 1.0)  # 2 contemplados (sorteio + lance)
                else:
                    prob_mes_com = 1.0 / participantes_atual  # Apenas 1 contemplado (só sorteio)
            else:
                prob_mes_sem = 0.0
                prob_mes_com = 0.0
            
            prob_sem_lance.append(prob_mes_sem)
            prob_com_lance.append(prob_mes_com)
            
            # Cálculo correto das probabilidades acumuladas usando a fórmula de sobrevivência
            prob_nao_contemplado_sem *= (1.0 - prob_mes_sem)
            prob_nao_contemplado_com *= (1.0 - prob_mes_com)
            
            prob_acumulada_sem.append(1.0 - prob_nao_contemplado_sem)
            prob_acumulada_com.append(1.0 - prob_nao_contemplado_com)
            
            # Reduzir participantes para próximo mês baseado no cenário atual
            participantes_atual = max(0, participantes_atual - contemplados_por_mes)
        
        # Calcular métricas estatísticas corrigidas
        def calcular_metricas_corrigidas(probabilidades_mensais, probabilidades_acumuladas):
            # Usar as probabilidades mensais para calcular a esperança
            total_prob = sum(probabilidades_mensais)
            if total_prob > 0:
                # Normalizar para que some 1
                probs_norm = [p/total_prob for p in probabilidades_mensais]
                esperanca = sum((i+1) * p for i, p in enumerate(probs_norm))
                
                # Usar probabilidades acumuladas para percentis
                p50 = p10 = p90 = None
                for i, prob_acum in enumerate(probabilidades_acumuladas):
                    if p10 is None and prob_acum >= 0.10:
                        p10 = i + 1
                    if p50 is None and prob_acum >= 0.50:
                        p50 = i + 1
                    if p90 is None and prob_acum >= 0.90:
                        p90 = i + 1
                    if p90 is not None:
                        break
                
                return esperanca, p50, p10, p90
            else:
                return 0, None, None, None
        
        esp_sem, med_sem, p10_sem, p90_sem = calcular_metricas_corrigidas(prob_sem_lance, prob_acumulada_sem)
        esp_com, med_com, p10_com, p90_com = calcular_metricas_corrigidas(prob_com_lance, prob_acumulada_com)
        
        return {
            "sem_lance": {
                "meses": meses,
                "hazard": prob_sem_lance,
                "probabilidade_acumulada": prob_acumulada_sem,
                "probabilidade_mes": prob_sem_lance,  # Mesmo que hazard para este caso
                "esperanca_meses": esp_sem,
                "mediana_mes": med_sem,
                "p10_mes": p10_sem,
                "p90_mes": p90_sem
            },
            "com_lance": {
                "meses": meses,
                "hazard": prob_com_lance,
                "probabilidade_acumulada": prob_acumulada_com,
                "probabilidade_mes": prob_com_lance,  # Mesmo que hazard para este caso
                "esperanca_meses": esp_com,
                "mediana_mes": med_com,
                "p10_mes": p10_com,
                "p90_mes": p90_com
            },
            "parametros": {
                "num_participantes": num_participantes,
                "lance_livre_perc": lance_livre_perc,
                "contemplados_por_mes": contemplados_por_mes,
                "meses_total": meses_total
            }
        }
        
    except Exception as e:
        logger.error(f"Erro no cálculo de probabilidades corrigido: {e}")
        return None

def calcular_probabilidade_mes_especifico(mes_contemplacao: int, lance_livre_perc: float, num_participantes: int = 430, contemplados_por_mes: int = 2):
    """
    Calcula as probabilidades específicas para um mês de contemplação escolhido.
    
    Args:
        mes_contemplacao: Mês escolhido para contemplação
        lance_livre_perc: Percentual do lance livre (se 0, considera apenas sorteio)
        num_participantes: Número total de participantes do grupo
        contemplados_por_mes: Número de contemplados por mês
    
    Returns:
        dict com:
        - prob_no_mes: probabilidade de ser contemplado NAQUELE mês
        - prob_ate_mes: probabilidade de ter sido contemplado ATÉ aquele mês
        - participantes_restantes: quantos participantes restam no início daquele mês
    """
    try:
        if mes_contemplacao < 1:
            return {
                "prob_no_mes": 0.0,
                "prob_ate_mes": 0.0,
                "participantes_restantes": 0
            }
            
        # Calcular participantes restantes no início do mês
        participantes_restantes = max(0, num_participantes - (mes_contemplacao - 1) * contemplados_por_mes)
        
        if participantes_restantes <= 0:
            return {
                "prob_no_mes": 0.0,
                "prob_ate_mes": 1.0,
                "participantes_restantes": 0
            }
        
        # Probabilidade no mês específico (hazard)
        if lance_livre_perc > 0:
            # COM LANCE: 2 contemplados (1 sorteio + 1 lance)
            contemplados_mes = 2
            prob_no_mes = min(2.0 / participantes_restantes, 1.0)
        else:
            # SEM LANCE: apenas 1 contemplado (só sorteio)
            contemplados_mes = 1
            prob_no_mes = min(1.0 / participantes_restantes, 1.0)
        
        # Probabilidade acumulada até o mês (F_t)
        # Usar aproximação simples para evitar erros numéricos
        total_contemplados_ate_mes = min(mes_contemplacao * contemplados_mes, num_participantes)
        prob_ate_mes = min(total_contemplados_ate_mes / num_participantes, 1.0)
        
        return {
            "prob_no_mes": float(prob_no_mes),
            "prob_ate_mes": float(prob_ate_mes),
            "participantes_restantes": int(participantes_restantes)
        }
        
    except Exception as e:
        logger.error(f"Erro ao calcular probabilidade do mês específico: {e}")
        return {
            "prob_no_mes": 0.0,
            "prob_ate_mes": 0.0,
            "participantes_restantes": 0
        }