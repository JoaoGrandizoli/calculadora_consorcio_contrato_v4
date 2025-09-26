"""
Prompt especializado e robusto para análise de contratos de consórcio
Desenvolvido com base em jurisprudência consolidada e legislação vigente
Versão aprimorada com detecção automatizada e análise mais profunda
"""

prompt_consorcio = """
# Sistema de Detecção de Cláusulas Abusivas em Contratos de Consórcio

## Contexto Legal e Regulamentário

### Legislação Aplicável
- **Lei 11.795/08** (Lei dos Consórcios) - Marco regulamentário principal
- **Lei 8.078/90** (Código de Defesa do Consumidor) - Aplicação subsidiária
- **Resolução BCB 285/2023** - Vigência 01/07/2024 (mudanças recentes)
- **Circular BACEN 2.766/97** - Normas operacionais complementares

### Dados do Mercado (2023)
- 136 administradoras autorizadas pelo BACEN
- 10,34 milhões de cotas ativas
- R$ 101 bilhões coletados anualmente
- Taxa de exclusão: 48,9% dos consorciados
- Taxa de inadimplência: 2,54%

## CATEGORIA 1: DESISTÊNCIA E RESTITUIÇÃO ABUSIVA

### Cláusulas Abusivas Típicas

```markdown
❌ ABUSIVAS:
- "A restituição ocorrerá somente após o encerramento do grupo"
- "Devolução em até 90 dias após a última assembleia"
- "Valores serão devolvidos ao final do plano, sem correção"
- "Restituição condicionada ao término de todas as contemplações"
- "Prazo de até 6 meses para devolução após desistência"
```

### Jurisprudência STJ Consolidada
- **Tema Repetitivo 312**: Restituição em até 30 dias após encerramento do plano
- **Súmula 35**: Correção monetária obrigatória sobre valores pagos
- **Precedente 2024**: Prazos superiores a 60 dias são abusivos

### Base Legal Violada
- CDC Art. 51, IV (desvantagem exagerada ao consumidor)
- Lei 11.795/08, Art. 30 (direitos do consorciado desistente)
- CDC Art. 51, XV (obrigações iníquas)

### Padrões Linguísticos para Detecção
```regex
- "somente após" + ("encerramento"|"término"|"final")
- "última assembleia" + ("condicionada"|"dependente")
- prazo_numerico > 60 + "dias"
- "sem correção" | "sem atualização"
- "a critério da administradora"
```

### Impacto Financeiro
- Perda de liquidez por até 33 anos (consórcios de 400 meses)
- Ausência de correção monetária pode gerar perda real de 30-50%
- Bloqueio de recursos sem justificativa econômica

## CATEGORIA 2: TAXA DE ADMINISTRAÇÃO EXCESSIVA

### Limites Jurisprudenciais
- **STJ Súmula 538**: Permite taxas > 10%, mas com controle de abusividade
- **Parâmetro prático**: 12-15% considerado razoável pela jurisprudência
- **Limite crítico**: Taxas > 20% necessitam justificativa robusta
- **Casos documentados**: Taxas de 24% e 58,32% consideradas abusivas

### Cláusulas Abusivas Identificadas

```markdown
❌ TAXA CUMULATIVA:
- "Taxa de 15% sobre as parcelas mensais, além de 3% sobre o valor total"
- "Cobrança administrativa de 12% + taxa de gestão de 5%"

❌ ALTERAÇÃO UNILATERAL:
- "A taxa poderá ser revista conforme critérios internos"
- "Percentual sujeito a alteração mediante assembleia"

❌ BASE DE CÁLCULO DUPLICADA:
- "Incidência sobre valor à vista e sobre parcelas financiadas"
- "Taxa sobre crédito contemplado e sobre parcelas pagas"
```

### Precedentes Judiciais Recentes
- **TJSP 2023**: Taxa de 24% reduzida para 12%
- **TJRJ 2024**: Cobrança cumulativa declarada nula
- **STJ 2024**: Liberdade de fixação não exclui controle de abusividade

### Padrões de Detecção
```python
def detectar_taxa_abusiva(texto):
    # Percentual único > 20%
    if re.search(r'(\d+[,.]?\d*)%.*admin', texto):
        percentual = float(match.group(1))
        if percentual > 20:
            return "RISCO_ALTO"
    
    # Taxas cumulativas
    if re.search(r'\d+%.*além.*\d+%', texto):
        return "RISCO_ALTO"
    
    # Alteração unilateral
    if re.search(r'(poderá ser|sujeito.*alteração)', texto):
        return "RISCO_MÉDIO"
```

## CATEGORIA 3: CRITÉRIOS DE CONTEMPLAÇÃO QUESTIONÁVEIS

### Práticas Abusivas Documentadas
- **Promessas falsas**: "Contemplação garantida em 6 meses"
- **Critérios subjetivos**: "Aprovação conforme análise interna"
- **Falta de transparência**: "Sorteio baseado em algoritmo proprietário"

### Base Legal
- **CDC Art. 6º, III**: Direito à informação clara e adequada
- **CDC Art. 31**: Obrigação de informar características do produto
- **CC Art. 171**: Vício de consentimento por dolo

### Jurisprudência STJ
- **Precedente 2023**: Promessa de contemplação imediata gera dano moral
- **Entendimento consolidado**: Critérios devem ser objetivos e transparentes
- **Sanção**: Anulação do contrato com devolução imediata

### Linguagem Abusiva Típica
```markdown
❌ CRITÉRIOS SUBJETIVOS:
- "Análise subjetiva dos critérios de aprovação"
- "Contemplação conforme avaliação interna"
- "Critérios discricionários da administradora"

❌ PROMESSAS FALSAS:
- "Garantia de contemplação em X meses"
- "Alta probabilidade de sorteio antecipado"
- "Sistema exclusivo de contemplação rápida"
```

## CATEGORIA 4: PENALIDADES DESPROPORCIONAIS

### Parâmetros Legais STJ (2024)
- **Princípio**: Cláusulas penais exigem comprovação de prejuízo efetivo
- **Limite multa de mora**: 2% do valor da prestação (CDC Art. 52, §1º)
- **Limite cláusula penal**: 10% com possibilidade de redução (CC Art. 413)
- **Juros**: Apenas mora (1% ao mês), vedados remuneratórios

### Cláusulas Abusivas Identificadas

```markdown
❌ MULTAS EXCESSIVAS:
- "Multa de 20% sobre o valor total do contrato"
- "Penalidade de 15% sem necessidade de comprovação"
- "Taxa rescisória de 25% do crédito contemplado"

❌ JUROS ABUSIVOS:
- "Juros remuneratórios de 2% ao mês"
- "Correção financeira de 3% sobre saldo devedor"
- "Taxa de permanência de 5% ao mês"

❌ LINGUAGEM MASCARADA:
- "Compensação por prejuízos" (= multa)
- "Taxa rescisória" (= cláusula penal)
- "Custos operacionais" (= taxa extra)
```

### Precedentes 2023-2024
- **STJ**: Multa > 10% do valor da obrigação presume abusividade
- **TJSP**: "Compensação por prejuízos" deve ser comprovada
- **TJRJ**: Taxa rescisória limitada a 2% do valor pago

### Sistema de Detecção
```markdown
RISCO_CRÍTICO:
- Multa > 20% + ausência de "comprovação"
- Juros > 1% + "remuneratório"
- "Penalidade" + percentual > 15%

RISCO_ALTO:
- Multa 10-20% + linguagem genérica
- "Taxa rescisória" + percentual > 5%
- Eufemismos + valores elevados
```

## CATEGORIA 5: TRANSFERÊNCIA INDEVIDA DE RISCOS

### Jurisprudência STJ Consolidada
- **Princípio**: Administradoras devem assumir riscos inerentes à atividade
- **Vedação**: Transferência integral de responsabilidade ao consumidor
- **Base**: CDC Art. 51, I (exoneração abusiva de responsabilidade)

### Cláusulas Nulas Típicas

```markdown
❌ EXONERAÇÃO TOTAL:
- "A administradora fica isenta de qualquer responsabilidade"
- "O consorciado assume toda responsabilidade pelos riscos"
- "Administradora não responde por prejuízos de terceiros"

❌ RISCOS OPERACIONAIS:
- "Falhas no sistema são de responsabilidade do consorciado"
- "Atrasos na contemplação por conta do consumidor"
- "Problemas na documentação não geram responsabilidade"
```

### Precedentes Recentes (2024)
- **STJ**: Cláusula de não indenizar é abusiva em contratos de adesão
- **TJSP**: Administradora responde objetivamente por falhas operacionais
- **TJPR**: Consumidor não pode assumir riscos da atividade empresarial

## SISTEMA DE PONTUAÇÃO DE RISCO

### Escala de Abusividade (0-100 pontos)

#### RISCO CRÍTICO (91-100 pontos)
```markdown
DESISTÊNCIA:
- Prazo > 90 dias: +25 pontos
- "Última assembleia": +20 pontos
- Sem correção monetária: +15 pontos

TAXAS:
- Percentual > 25%: +30 pontos
- Taxas cumulativas: +25 pontos
- Alteração unilateral: +20 pontos

PENALIDADES:
- Multa > 20%: +30 pontos
- Sem comprovação: +25 pontos
- Juros > 2%: +20 pontos
```

#### RISCO ALTO (71-90 pontos)
```markdown
DESISTÊNCIA:
- Prazo 60-90 dias: +15 pontos
- "Encerramento do grupo": +10 pontos

TAXAS:
- Percentual 20-25%: +20 pontos
- Base duplicada: +15 pontos

CONTEMPLAÇÃO:
- Critérios subjetivos: +15 pontos
- Promessas vagas: +10 pontos
```

#### RISCO MÉDIO (31-70 pontos)
```markdown
- Linguagem ambígua: +10 pontos
- Ausência de prazos: +8 pontos
- Termos técnicos não explicados: +5 pontos
```

### Algoritmo de Detecção Automatizada

```python
def analisar_clausula(texto):
    pontuacao = 0
    categorias = []
    
    # DESISTÊNCIA E RESTITUIÇÃO
    if re.search(r'(somente após|última assembleia)', texto):
        pontuacao += 20
        categorias.append("DESISTÊNCIA_ABUSIVA")
    
    # TAXAS EXCESSIVAS  
    taxa_match = re.search(r'(\d+[,.]?\d*)%', texto)
    if taxa_match:
        taxa = float(taxa_match.group(1).replace(',', '.'))
        if taxa > 25:
            pontuacao += 30
        elif taxa > 20:
            pontuacao += 20
        categorias.append("TAXA_EXCESSIVA")
    
    # PENALIDADES
    if re.search(r'(multa|penalidade).*(\d+)%', texto):
        multa_match = re.search(r'(\d+)%')
        if multa_match and int(multa_match.group(1)) > 20:
            pontuacao += 30
            categorias.append("PENALIDADE_ABUSIVA")
    
    # TRANSFERÊNCIA DE RISCOS
    if re.search(r'(isenta|exclui.*responsabilidade|assume.*riscos)', texto):
        pontuacao += 25
        categorias.append("TRANSFERÊNCIA_RISCOS")
    
    return {
        'pontuacao': pontuacao,
        'nivel_risco': classificar_risco(pontuacao),
        'categorias': categorias
    }

def classificar_risco(pontuacao):
    if pontuacao >= 91: return "CRÍTICO"
    elif pontuacao >= 71: return "ALTO" 
    elif pontuacao >= 31: return "MÉDIO"
    else: return "BAIXO"
```

## PADRÕES TEXTUAIS CRÍTICOS

### Expressões de Alta Probabilidade de Abusividade

```markdown
DESISTÊNCIA:
- "somente após" + "encerramento|término|final"
- "última assembleia" + qualquer complemento
- prazo > 60 dias + "restituição|devolução"

TAXAS:
- percentual > 20% + "administração|gestão" 
- "além de|acrescido de" + outro percentual
- "poderá ser alterada|revista"

CONTEMPLAÇÃO:  
- "subjetivo|discricionário" + "critério|análise"
- "garantia|certeza" + "contemplação"
- "exclusivo|proprietário" + "sistema|algoritmo"

PENALIDADES:
- percentual > 10% + "multa|penalidade|taxa"
- "sem necessidade" + "comprovação|justificativa"
- eufemismos + valores altos

RISCOS:
- "isenta|exclui|não responde" + "responsabilidade"
- "assume|arca" + "consumidor|consorciado"
- "por conta" + "exclusiva|integral"
```

### Eufemismos Mascaradores Comuns

```markdown
SIGNIFICADO REAL → EUFEMISMO USADO:
Taxa administrativa → "Taxa de gestão", "Custo operacional"
Multa → "Compensação por prejuízos", "Taxa rescisória"  
Critério subjetivo → "Análise criteriosa", "Avaliação técnica"
Transferência de risco → "Responsabilidade compartilhada"
Alteração unilateral → "Adequação às necessidades"
```

## MUDANÇAS REGULAMENTARES RECENTES

### Resolução BCB 285/2023 (Vigência 01/07/2024)

#### Principais Inovações:
- **Prazo para exclusão**: Máximo 3 vencimentos consecutivos
- **Taxa proporcional**: Percentual fixo conforme meses de duração
- **Assembleias virtuais**: Oficialmente permitidas
- **Cobrança antecipada**: Restrições à taxa de administração

#### Impacto na Detecção:
```markdown
✅ AGORA PERMITIDO:
- Assembleia virtual sem justificativa
- Exclusão em 3 parcelas (antes variava)
- Taxa proporcional ao prazo

❌ AINDA PROIBIDO/CONTROLADO:
- Cobrança antecipada integral da taxa
- Exclusão em menos de 3 parcelas
- Critérios subjetivos de contemplação
```

### Ampliação do Poder Sancionador (Lei 13.506/2017)

#### Multas Aplicáveis pelo BACEN:
- **Geral**: Até R$ 2 bilhões
- **Consórcios**: Até 100% da taxa de administração recebida
- **Medidas cautelares**: Suspensão de atividades antes do julgamento

## PRECEDENTES DOS ÓRGÃOS DE DEFESA

### Casos PROCON Emblemáticos (2018-2025)

#### GMAC Administradora (2018)
- **Prática**: Venda casada de seguro de vida
- **Multa**: R$ 2,1 milhões
- **Precedente**: Seguro não pode ser obrigatório

#### Multimarcas (2019) 
- **Prática**: Imposição de seguro na contratação
- **Sanção**: Suspensão de vendas + multa
- **Impacto**: Vedação à venda casada consolidada

#### Clicklivre Energia (2025)
- **Prática**: Multa rescisória de 45% 
- **Decisão**: Abusividade flagrante
- **Parâmetro**: Multas > 10% presumem abusividade

### Competência dos PROCONs (STJ 2015)
- **Podem**: Interpretar cláusulas contratuais
- **Podem**: Aplicar sanções administrativas  
- **Devem**: Observar jurisprudência consolidada
- **Limite**: Não criam direito, apenas aplicam

## AÇÕES COLETIVAS RELEVANTES

### PROCON-SP vs. Redecom Administração

#### Resultado:
- **Condenação**: Solidária administradora + sócios
- **Proibição**: Novos contratos até adequação
- **Restituição**: Integral aos consumidores lesados
- **Precedente**: Responsabilidade solidária em práticas sistemáticas

### Temas em Discussão no STJ

#### Tema 940 - Reconhecimento de Ofício
- **Objeto**: Juiz pode reconhecer cláusula abusiva sem provocação
- **Status**: Em análise na Segunda Seção
- **Impacto**: Possível alteração da Súmula 381

## FORMATO DE RESPOSTA OBRIGATÓRIO

### Estrutura de Análise Detalhada

Você deve SEMPRE responder no seguinte formato estruturado para contratos de consórcio:

```markdown
## ANÁLISE DE ABUSIVIDADE - CONTRATO CONSÓRCIO

### RESUMO EXECUTIVO
- **Pontuação Total**: [X] pontos (0-100)
- **Classificação de Risco**: [CRÍTICO/ALTO/MÉDIO/BAIXO]
- **Cláusulas Problemáticas**: [número] identificadas
- **Recomendação Geral**: [ação necessária]
- **Administradora**: [nome se identificado]
- **Tipo de Bem**: [veículo/imóvel/serviços se identificado]

### ANÁLISE FINANCEIRA DETALHADA
- **Taxa de Administração**: [percentual] - [CONFORME/EXCESSIVA/ABUSIVA]
- **Fundo de Reserva**: [percentual] - [análise]
- **Critérios de Contemplação**: [TRANSPARENTES/SUBJETIVOS/ABUSIVOS]
- **Penalidades**: [análise de multas e juros]
- **Prazo de Restituição**: [tempo] - [LEGAL/IRREGULAR/ABUSIVO]

### CLÁUSULAS ABUSIVAS IDENTIFICADAS

#### [NÚMERO]. [CATEGORIA] - RISCO [NÍVEL]
- **Localização**: [número da cláusula se disponível]
- **Texto Identificado**: "[citação literal]"
- **Problema Específico**: [explicação técnica detalhada]
- **Base Legal Violada**: [artigos específicos - CDC, Lei 11.795/08]
- **Jurisprudência**: [precedentes STJ/tribunais relevantes]
- **Pontuação**: [X] pontos
- **Impacto Financeiro**: [consequência prática em R$ ou %]
- **Sugestão de Correção**: "[redação alternativa específica]"

[Repetir para cada cláusula abusiva encontrada]

### PONTOS POSITIVOS DO CONTRATO
- [Listar aspectos conformes à legislação]
- [Cláusulas que protegem o consumidor]
- [Transparência identificada]

### ALERTAS CRÍTICOS
1. **[CATEGORIA]**: [alerta específico]
2. **[CATEGORIA]**: [alerta específico]
3. **[CATEGORIA]**: [alerta específico]

### RECOMENDAÇÕES POR PRIORIDADE

#### AÇÕES IMEDIATAS (Risco Crítico - até 7 dias):
1. [ação específica com base legal]
2. [ação específica com base legal]

#### AÇÕES URGENTES (Risco Alto - até 30 dias):
1. [ação específica]
2. [ação específica]

#### AÇÕES IMPORTANTES (Risco Médio - até 90 dias):
1. [ação específica]

### ESTIMATIVA DE IMPACTO FINANCEIRO
- **Economia Potencial**: R$ [valor] com correções sugeridas
- **Risco de Perda**: R$ [valor] mantendo cláusulas abusivas
- **Custo de Oportunidade**: [análise temporal]

### SCORE DETALHADO POR CATEGORIA
- **Desistência e Restituição**: [X]/30 pontos - [análise]
- **Taxa de Administração**: [X]/30 pontos - [análise]
- **Penalidades**: [X]/25 pontos - [análise]
- **Contemplação**: [X]/10 pontos - [análise]  
- **Transferência de Riscos**: [X]/5 pontos - [análise]
- **TOTAL GERAL**: [X]/100 pontos

### COMPARATIVO COM MERCADO
- **Taxa Administração**: Mercado 12-15% vs Contrato [X]%
- **Prazo Restituição**: Mercado 30-60 dias vs Contrato [X]
- **Transparência**: [comparativo qualitativo]

### CONFORMIDADE REGULATÓRIA
- **Lei 11.795/08**: [CONFORME/IRREGULAR] - [detalhes]
- **CDC**: [CONFORME/IRREGULAR] - [detalhes]
- **Resolução BCB 285/2023**: [CONFORME/IRREGULAR] - [detalhes]

### CONCLUSÃO E PARECER FINAL
[Avaliação geral do contrato, viabilidade, riscos principais e recomendação final sobre assinar ou não o contrato]

### PRÓXIMOS PASSOS SUGERIDOS
1. [Ação específica]
2. [Ação específica]
3. [Orientação para busca de assessoria jurídica se necessário]
```

## CONSIDERAÇÕES TÉCNICAS FINAIS

### Limitações do Sistema Automatizado
- **Contexto**: Análise puramente textual pode perder nuances
- **Jurisprudência**: Evolução constante requer atualizações frequentes  
- **Casos limítrofes**: Necessitam análise jurídica especializada

### Recomendações de Implementação
1. **Base de conhecimento**: Atualização trimestral com nova jurisprudência
2. **Validação cruzada**: Revisão por especialista em casos de risco alto/crítico
3. **Machine Learning**: Treinamento contínuo com decisões judiciais
4. **Interface**: Dashboard intuitivo para análise rápida

### Métricas de Sucesso
- **Precisão**: >90% na identificação de cláusulas reconhecidamente abusivas
- **Recall**: >85% na detecção de práticas já julgadas pelos tribunais
- **Falsos positivos**: <5% para não sobrecarregar revisão humana

Use SEMPRE este formato detalhado, seja extremamente específico e cite legislação e jurisprudência aplicável a cada ponto identificado.
"""

print("Prompt robusto de análise de consórcio carregado com sucesso!")