import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Separator } from './components/ui/separator';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { AlertCircle, Calculator, TrendingUp, FileText, PieChart, Download, Settings, Loader, Target } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import CadastroForm from './components/CadastroForm';
import AdminPanel from './components/AdminPanel';
import ContractAnalysis from './components/ContractAnalysis';
import './App.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Chart.js options
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
    },
    title: {
      display: false,
    },
  },
  scales: {
    y: {
      beginAtZero: true,
    },
  },
};

function App() {
  // Estado para controle de acesso
  const [hasAccess, setHasAccess] = useState(false);
  const [accessToken, setAccessToken] = useState(null);
  const [leadInfo, setLeadInfo] = useState(null);
  const [showAdmin, setShowAdmin] = useState(false);
  const [adminAuthenticated, setAdminAuthenticated] = useState(false);
  const [adminPassword, setAdminPassword] = useState('');
  const [adminLoginError, setAdminLoginError] = useState('');
  
  // Estado para controlar abas principais
  const [activeTab, setActiveTab] = useState('simulador');

  // 🔧 FIX CRÍTICO: Verificar acesso admin apenas por URL, não por localStorage
  // localStorage serve apenas para persistir APÓS a autenticação
  const isAdminAccess = window.location.pathname === '/admin' || 
                        window.location.hash === '#admin';

  const [parametros, setParametros] = useState({
    valor_carta: 100000,
    prazo_meses: 120,
    taxa_admin: 0.21,
    fundo_reserva: 0.03,
    mes_contemplacao: 1,
    lance_livre_perc: 0.10,
    taxa_reajuste_anual: 0.05
  });

  const [resultados, setResultados] = useState(null);
  const [probabilidades, setProbabilidades] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [loadingProb, setLoadingProb] = useState(false);
  const [erro, setErro] = useState(null);
  const [parametrosProb, setParametrosProb] = useState({
    num_participantes: 430,
    lance_livre_perc: 0.10
  });
  const [mostrarDetalheProbabilidades, setMostrarDetalheProbabilidades] = useState(false);

  // Verificar acesso ao carregar a página
  useEffect(() => {
    console.log('🔧 Inicializando aplicação...');
    
    const storedToken = localStorage.getItem('access_token');
    const adminAuth = localStorage.getItem('admin_authenticated') === 'true';
    const currentUrl = window.location.href;
    
    // 🔧 NOVA LÓGICA: Capturar parâmetros do redirect do Typeform
    const urlParams = new URLSearchParams(window.location.search);
    const emailFromUrl = urlParams.get('email');
    const timestampFromUrl = urlParams.get('t');
    const submittedFlag = urlParams.get('submitted');
    
    console.log('🔧 Estado inicial:', { 
      storedToken: !!storedToken, 
      adminAuth, 
      isAdminAccess,
      currentUrl,
      emailFromUrl,
      timestampFromUrl,
      submittedFlag
    });
    
    // 🎯 PRIORIDADE 1: Se chegou do Typeform via redirect (email + timestamp na URL)
    if (emailFromUrl && timestampFromUrl && submittedFlag === 'true') {
      console.log('🎯 REDIRECT DO TYPEFORM DETECTADO!');
      console.log('📧 Email da URL:', emailFromUrl);
      console.log('⏰ Timestamp da URL:', timestampFromUrl);
      
      // Buscar lead específico por email e timestamp
      findLeadByEmailAndTimestamp(emailFromUrl, timestampFromUrl);
      return; // Não continuar com outras verificações
    }
    
    // Resto da lógica original...
    if (storedToken) {
      setAccessToken(storedToken);
      checkAccessToken(storedToken);
    }
    
    // 🔐 CORREÇÃO: Separar detecção de URL da persistência de estado
    if (isAdminAccess) {
      // Usuário está acessando URL de admin diretamente
      console.log('🔐 URL de admin detectada');
      
      if (adminAuth) {
        console.log('🔐 Admin já autenticado - ativando modo admin');
        setAdminAuthenticated(true);
        setShowAdmin(true);
        setHasAccess(true);
        localStorage.setItem('admin_mode', 'true');
      } else {
        console.log('🔐 Solicitando autenticação admin');
        setShowAdmin(true);
        setHasAccess(true);
        // NÃO definir admin_mode aqui - só após autenticação
      }
    } else {
      // Usuário NÃO está em URL de admin
      console.log('🔧 URL normal detectada');
      
      if (adminAuth && localStorage.getItem('admin_mode') === 'true') {
        // Se estava no admin e ainda tem sessão válida, manter apenas se explicitamente solicitado
        console.log('🔧 Sessão admin existente, mas fora da URL admin - limpando modo admin');
        localStorage.removeItem('admin_mode');
        setShowAdmin(false);
      }
      
      // Garantir que não está em modo admin se não é URL admin
      setShowAdmin(false);
    }
  }, [isAdminAccess]);

  // Carregar parâmetros padrão ao inicializar
  useEffect(() => {
    const carregarParametrosPadrao = async () => {
      try {
        const response = await axios.get(`${API}/parametros-padrao`);
        setParametros(response.data);
      } catch (error) {
        console.error('Erro ao carregar parâmetros padrão:', error);
      }
    };
    carregarParametrosPadrao();
  }, []);

  const handleAccessGranted = (token) => {
    setAccessToken(token);
    setHasAccess(true);
    localStorage.setItem('access_token', token);
  };

  // 🔐 NOVA FUNÇÃO: Autenticação admin
  const handleAdminLogin = (password) => {
    const correctPassword = 'Joao@123'; // Senha definida
    
    if (password === correctPassword) {
      setAdminAuthenticated(true);
      setAdminLoginError('');
      localStorage.setItem('admin_authenticated', 'true');
      console.log('✅ Admin autenticado com sucesso');
      return true;
    } else {
      setAdminLoginError('Senha incorreta. Tente novamente.');
      console.log('❌ Falha na autenticação admin');
      return false;
    }
  };

  const handleAdminLogout = () => {
    setAdminAuthenticated(false);
    setShowAdmin(false);
    localStorage.removeItem('admin_authenticated');
    localStorage.removeItem('admin_mode');
    setAdminPassword('');
    setAdminLoginError('');
    console.log('🔐 Admin logout realizado');
  };

  // 🎯 NOVA FUNÇÃO: Buscar lead por email e timestamp do redirect do Typeform
  const findLeadByEmailAndTimestamp = async (email, timestamp) => {
    console.log('🔍 Buscando lead específico por email e timestamp...');
    console.log('📧 Email:', email);
    console.log('⏰ Timestamp:', timestamp);
    
    try {
      // Converter timestamp para Date para comparação
      const submissionTime = new Date(timestamp);
      const tenMinutesAgo = new Date(Date.now() - 10 * 60 * 1000); // 10 minutos de janela
      
      console.log('🕒 Janela de busca:', {
        submissionTime: submissionTime.toISOString(),
        tenMinutesAgo: tenMinutesAgo.toISOString()
      });
      
      // Buscar todos os leads
      const response = await axios.get(`${API}/admin/leads`);
      const leads = response.data.leads || [];
      
      console.log(`🔍 Verificando ${leads.length} leads...`);
      
      // Buscar lead exato por email
      const matchingLeads = leads.filter(lead => {
        const leadEmail = lead.email?.toLowerCase().trim();
        const targetEmail = email.toLowerCase().trim();
        const leadCreatedAt = new Date(lead.created_at);
        
        console.log(`📋 Verificando lead: ${lead.name} - ${leadEmail} - ${leadCreatedAt.toISOString()}`);
        
        return leadEmail === targetEmail && leadCreatedAt > tenMinutesAgo;
      });
      
      console.log(`📊 Leads compatíveis encontrados: ${matchingLeads.length}`);
      
      if (matchingLeads.length > 0) {
        // Pegar o mais recente se há múltiplos
        const selectedLead = matchingLeads.sort((a, b) => 
          new Date(b.created_at) - new Date(a.created_at)
        )[0];
        
        console.log('✅ LEAD ENCONTRADO POR EMAIL+TIMESTAMP:');
        console.log('   - Nome:', selectedLead.name);
        console.log('   - Email:', selectedLead.email);
        console.log('   - Token:', selectedLead.access_token);
        console.log('   - Criado em:', selectedLead.created_at);
        
        // Salvar dados no localStorage
        localStorage.setItem('access_token', selectedLead.access_token);
        localStorage.setItem('lead_data', JSON.stringify({
          leadId: selectedLead.id,
          name: selectedLead.name,
          email: selectedLead.email,
          token: selectedLead.access_token,
          timestamp: new Date().toISOString(),
          source: 'typeform_redirect'
        }));
        
        // Limpar parâmetros da URL
        window.history.replaceState({}, document.title, window.location.pathname);
        
        // Conceder acesso
        setAccessToken(selectedLead.access_token);
        setHasAccess(true);
        setLeadInfo({
          name: selectedLead.name,
          email: selectedLead.email,
          created_at: selectedLead.created_at
        });
        
        console.log('🎯 ACESSO CONCEDIDO VIA REDIRECT DO TYPEFORM');
        
      } else {
        console.log('❌ Nenhum lead encontrado com esse email e timestamp');
        console.log('🔄 Tentando busca por lead mais recente...');
        
        // Fallback: buscar lead mais recente
        const recentLead = leads.find(lead => {
          const leadCreatedAt = new Date(lead.created_at);
          return leadCreatedAt > tenMinutesAgo && 
                 lead.access_token && 
                 !lead.name.includes('João Silva') &&
                 !lead.name.includes('Test');
        });
        
        if (recentLead) {
          console.log('✅ FALLBACK - Lead recente encontrado:', recentLead.name);
          localStorage.setItem('access_token', recentLead.access_token);
          setAccessToken(recentLead.access_token);
          setHasAccess(true);
        } else {
          console.log('❌ Nenhum lead recente encontrado - redirecionando para formulário');
          // Não fazer nada, deixar mostrar o formulário
        }
      }
      
    } catch (error) {
      console.error('❌ Erro ao buscar lead por email/timestamp:', error);
      // Em caso de erro, não fazer nada e deixar o fluxo normal
    }
  };

  const checkAccessToken = async (token) => {
    try {
      // Verificar se o token não é muito antigo (evitar tokens de teste)
      const tokenData = localStorage.getItem('lead_data');
      if (tokenData) {
        const leadData = JSON.parse(tokenData);
        const tokenAge = Date.now() - new Date(leadData.timestamp || 0).getTime();
        
        // Se token tem mais de 24 horas, considerar inválido
        if (tokenAge > 24 * 60 * 60 * 1000) {
          console.log('🕒 Token expirado (>24h), limpando...');
          localStorage.removeItem('access_token');
          localStorage.removeItem('lead_data');
          setHasAccess(false);
          return;
        }
      }
      
      // Validar token no servidor
      const response = await axios.get(`${API}/check-access/${token}`);
      if (response.data.valid) {
        // 🔧 CORREÇÃO TEMPORÁRIA: Permitir tokens fallback para debug
        // TODO: Remover após webhook do Typeform estar funcionando
        const leadName = response.data.name || '';
        if (!leadName.includes('Teste') && 
            !leadName.includes('João Silva') && 
            !leadName.includes('Test') &&
            !token.startsWith('temp-') &&
            !token.startsWith('error-')) {
          
          console.log('✅ Token válido (incluindo fallback para debug):', token);
          setHasAccess(true);
          setAccessToken(token);
          setLeadInfo({
            name: response.data.name || 'Usuario Fallback',
            created_at: response.data.created_at
          });
        } else {
          console.log('🚮 Token de teste detectado, limpando...');
          localStorage.removeItem('access_token');
          localStorage.removeItem('lead_data');
          setHasAccess(false);
        }
      } else {
        console.log('❌ Token inválido no servidor');
        localStorage.removeItem('access_token');
        localStorage.removeItem('lead_data');
        setHasAccess(false);
      }
    } catch (error) {
      console.error('Erro ao verificar token:', error);
      // Em caso de erro, limpar token para segurança
      localStorage.removeItem('access_token');
      localStorage.removeItem('lead_data');
      setHasAccess(false);
    }
  };

  const handleInputChange = (field, value) => {
    setParametros(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const simularConsorcio = async () => {
    setLoading(true);
    setErro(null);
    
    try {
      const headers = {};
      
      // 🔧 DEBUG: Logs detalhados do estado atual
      console.log('🔍 ESTADO ATUAL ANTES DA SIMULAÇÃO:');
      console.log('   - accessToken (state):', accessToken);
      console.log('   - localStorage access_token:', localStorage.getItem('access_token'));
      console.log('   - localStorage lead_data:', localStorage.getItem('lead_data'));
      
      // 🔧 FIX DEFINITIVO: Garantir que o token seja sempre obtido
      let tokenParaUsar = accessToken;
      if (!tokenParaUsar) {
        // Fallback: tentar obter do localStorage diretamente
        tokenParaUsar = localStorage.getItem('access_token');
        if (tokenParaUsar) {
          setAccessToken(tokenParaUsar); // Sincronizar state
          console.log('🔧 Token recuperado do localStorage:', tokenParaUsar);
        }
      }
      
      if (tokenParaUsar) {
        headers.Authorization = `Bearer ${tokenParaUsar}`;
        console.log('🎯 Enviando Authorization header:', `Bearer ${tokenParaUsar.substring(0, 8)}...`);
        console.log('🎯 Token completo para debug:', tokenParaUsar);
      } else {
        console.warn('⚠️ AVISO: Nenhum access_token disponível para a simulação');
      }
      
      console.log('📡 Headers da requisição:', headers);
      
      const response = await axios.post(`${API}/simular`, parametros, { headers });
      
      if (response.data.erro) {
        setErro(response.data.mensagem);
        setResultados(null);
      } else {
        setResultados(response.data);
        console.log('✅ Simulação realizada com sucesso');
        
        // Buscar dados dos gráficos após simulação bem-sucedida
        try {
          // 1. Gráfico de Probabilidade
          const graficoProbResponse = await axios.get(`${API}/grafico-probabilidades/${parametros.prazo_meses}?lance_livre_perc=${parametros.lance_livre_perc}`);
          
          // 2. Gráfico de Fluxo de Caixa (usar detalhamento da simulação)
          const graficoFluxoData = response.data.detalhamento ? {
            labels: response.data.detalhamento.slice(0, 24).map((item, index) => `Mês ${index + 1}`),
            datasets: [
              {
                label: "Parcela Antes da Contemplação",
                data: response.data.detalhamento.slice(0, 24).map(item => item.parcela_antes || 0),
                borderColor: "rgb(255, 99, 132)",
                backgroundColor: "rgba(255, 99, 132, 0.2)",
                tension: 0.1,
                fill: false
              },
              {
                label: "Parcela Depois da Contemplação", 
                data: response.data.detalhamento.slice(0, 24).map(item => item.parcela_depois || 0),
                borderColor: "rgb(54, 162, 235)",
                backgroundColor: "rgba(54, 162, 235, 0.2)",
                tension: 0.1,
                fill: false
              }
            ]
          } : null;
          
          // 3. Gráfico de Saldo Devedor (usar detalhamento da simulação)
          const graficoSaldoData = response.data.detalhamento ? {
            labels: response.data.detalhamento.slice(0, 60).map((item, index) => `Mês ${index + 1}`),
            datasets: [
              {
                label: "Saldo Devedor",
                data: response.data.detalhamento.slice(0, 60).map(item => item.saldo_devedor || 0),
                borderColor: "rgb(75, 192, 192)",
                backgroundColor: "rgba(75, 192, 192, 0.2)",
                tension: 0.1,
                fill: true
              }
            ]
          } : null;
          
          // Adicionar todos os dados dos gráficos aos resultados
          setResultados(prevResultados => ({
            ...prevResultados,
            grafico_probabilidade: graficoProbResponse.data,
            grafico_fluxo: graficoFluxoData,
            grafico_saldo: graficoSaldoData
          }));
          
          console.log('✅ Dados dos gráficos carregados');
        } catch (graficoError) {
          console.error('⚠️ Erro ao carregar gráficos:', graficoError);
          // Não falhar a simulação se os gráficos não carregarem
        }
      }
    } catch (error) {
      console.error('❌ Erro na simulação:', error);
      setErro(error.response?.data?.detail || 'Erro ao simular consórcio');
      setResultados(null);
    } finally {
      setLoading(false);
    }
  };

  const formatarMoeda = (valor) => {
    return valor.toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    });
  };

  const formatarPorcentagem = (valor) => {
    return (valor * 100).toFixed(2) + '%';
  };

  const downloadRelatorioPdf = async () => {
    setLoadingPdf(true);
    
    try {
      console.log('📄 Iniciando download do relatório PDF...');
      
      const response = await axios.post(`${API}/gerar-relatorio-pdf`, parametros, {
        responseType: 'blob',
        headers: {
          'Accept': 'application/pdf'
        }
      });
      
      console.log('📄 Resposta recebida:', response.status, response.headers['content-type']);
      
      // Verificar se a resposta é válida
      if (response.status !== 200) {
        throw new Error(`Servidor retornou status ${response.status}`);
      }
      
      // Verificar se recebemos um PDF
      const contentType = response.headers['content-type'] || '';
      if (!contentType.includes('application/pdf')) {
        console.error('❌ Tipo de conteúdo inválido:', contentType);
        throw new Error('Resposta não é um PDF válido');
      }
      
      // Verificar se há dados
      if (!response.data || response.data.size === 0) {
        throw new Error('PDF recebido está vazio');
      }
      
      console.log('📄 PDF válido recebido, tamanho:', response.data.size, 'bytes');
      
      // 🔧 CORREÇÃO: Criar blob explicitamente com tipo PDF
      const blob = new Blob([response.data], { 
        type: 'application/pdf' 
      });
      
      console.log('📄 Blob criado, tamanho:', blob.size, 'bytes');
      
      // Nome do arquivo com timestamp
      const timestamp = new Date().toISOString().slice(0, 16).replace(/[:-]/g, '');
      const filename = `relatorio_consorcio_${timestamp}.pdf`;
      
      // 🔧 MÉTODO PRINCIPAL: Download via link temporário
      try {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.style.display = 'none';
        link.href = url;
        link.download = filename;
        link.setAttribute('download', filename);
        
        // Adicionar ao DOM, clicar e remover
        document.body.appendChild(link);
        console.log('📄 Iniciando download via link:', filename);
        
        link.click();
        
        // Cleanup
        setTimeout(() => {
          document.body.removeChild(link);
          window.URL.revokeObjectURL(url);
          console.log('📄 Download concluído e recursos liberados');
        }, 100);
        
      } catch (linkError) {
        console.warn('⚠️ Método de link falhou, tentando fallback:', linkError);
        
        // 🔧 FALLBACK: Tentar usar window.open
        try {
          const url = window.URL.createObjectURL(blob);
          const newWindow = window.open(url);
          if (newWindow) {
            console.log('📄 PDF aberto em nova janela como fallback');
            setTimeout(() => window.URL.revokeObjectURL(url), 1000);
          } else {
            throw new Error('Pop-up bloqueado');
          }
        } catch (fallbackError) {
          console.error('❌ Todos os métodos de download falharam:', fallbackError);
          throw new Error('Seu navegador bloqueou o download. Tente permitir pop-ups ou usar outro navegador.');
        }
      }
      
    } catch (error) {
      console.error('❌ Erro ao baixar relatório:', error);
      console.error('❌ Detalhes do erro:', error.response?.data || error.message);
      
      // Mostrar erro mais específico
      if (error.response?.status === 400) {
        setErro('Erro nos parâmetros da simulação. Verifique os valores e tente novamente.');
      } else if (error.response?.status === 500) {
        setErro('Erro interno do servidor. Tente novamente em alguns momentos.');
      } else if (error.message.includes('navegador bloqueou')) {
        setErro('Download bloqueado pelo navegador. Verifique as configurações de pop-up ou tente outro navegador.');
      } else {
        setErro(`Erro ao gerar relatório PDF: ${error.message}`);
      }
    } finally {
      setLoadingPdf(false);
    }
  };

  const calcularProbabilidades = async () => {
    setLoadingProb(true);
    setErro(null);
    
    try {
      const response = await axios.post(`${API}/calcular-probabilidades`, parametrosProb);
      
      if (response.data.erro) {
        setErro(response.data.mensagem);
        setProbabilidades(null);
      } else {
        setProbabilidades(response.data);
      }
    } catch (error) {
      setErro(error.response?.data?.detail || 'Erro ao calcular probabilidades');
      setProbabilidades(null);
    } finally {
      setLoadingProb(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-dark via-primary to-secondary">
      {!hasAccess && !isAdminAccess ? (
        /* Mostrar tela de Lead Capture */
        <div className="container mx-auto px-4 md:px-6 py-8">
          <CadastroForm onAccessGranted={handleAccessGranted} />
        </div>
      ) : showAdmin || isAdminAccess ? (
        /* 🔐 PROTEÇÃO ADMIN: Mostrar login ou painel conforme autenticação */
        !adminAuthenticated ? (
          /* Tela de Login Admin */
          <div className="min-h-screen bg-gray-50 flex items-center justify-center">
            <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8">
              <div className="text-center mb-8">
                <div className="mx-auto h-12 w-12 bg-red-100 rounded-full flex items-center justify-center mb-4">
                  <Settings className="h-6 w-6 text-red-600" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900">Acesso Administrativo</h2>
                <p className="text-gray-600 mt-2">Digite a senha para acessar o painel admin</p>
              </div>
              
              <form onSubmit={(e) => {
                e.preventDefault();
                console.log('🔐 Tentativa de login com senha:', adminPassword);
                const success = handleAdminLogin(adminPassword);
                if (success) {
                  console.log('🔐 Login bem-sucedido, atualizando estado...');
                  // Forçar atualização do estado
                  setTimeout(() => {
                    setShowAdmin(true);
                    localStorage.setItem('admin_mode', 'true');
                  }, 100);
                }
              }}>
                <div className="mb-4">
                  <Label htmlFor="adminPassword" className="block text-sm font-medium text-gray-700 mb-2">
                    Senha de Administrador
                  </Label>
                  <Input
                    id="adminPassword"
                    type="password"
                    value={adminPassword}
                    onChange={(e) => setAdminPassword(e.target.value)}
                    className="w-full"
                    placeholder="Digite a senha..."
                    required
                  />
                  {adminLoginError && (
                    <p className="mt-2 text-sm text-red-600">{adminLoginError}</p>
                  )}
                </div>
                
                <Button 
                  type="submit"
                  className="w-full bg-red-600 hover:bg-red-700 text-white"
                >
                  Entrar no Admin
                </Button>
              </form>
              
              <div className="mt-6 text-center">
                <button 
                  onClick={() => {
                    setShowAdmin(false);
                    localStorage.removeItem('admin_mode');
                    window.location.hash = '';
                  }}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Voltar ao simulador
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Painel Admin Autenticado */
          <div>
            <div className="bg-white border-b border-gray-200 px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <img 
                    src="/logo.png" 
                    alt="Logo" 
                    className="h-6 w-6 object-contain" 
                  />
                  <h1 className="text-xl font-semibold text-gray-900">Painel Administrativo</h1>
                </div>
                <button
                  onClick={handleAdminLogout}
                  className="flex items-center gap-2 px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
                >
                  Sair do Admin
                </button>
              </div>
            </div>
            <AdminPanel />
          </div>
        )
      ) : (
        /* 🎯 CONTEÚDO PRINCIPAL - Simulador com abas quando tem acesso */
        <div className="container mx-auto px-6 py-6">
          {/* Header Principal */}
          <div className="flex items-center gap-3 justify-between mb-6">
            <div className="flex items-center gap-4">
              <img 
                src="/logo.png" 
                alt="Logo" 
                className="h-12 w-12 object-contain" 
              />
              <Calculator className="h-8 w-8 text-accent-warm" />
              <div>
                <h1 className="text-2xl font-bold">Portal de Análise de Consórcio</h1>
                <p className="text-neutral-light opacity-90">Simulações e análises inteligentes para consórcios</p>
              </div>
            </div>
            
            {hasAccess && leadInfo && (
              <div className="text-right flex items-center gap-4">
                <button
                  onClick={() => {
                    const newAdminState = !showAdmin;
                    
                    if (newAdminState) {
                      // Entrando no modo admin - verificar autenticação
                      const isAuthenticated = localStorage.getItem('admin_authenticated') === 'true';
                      
                      // Mudar URL para admin
                      window.location.hash = '#admin';
                      
                      if (isAuthenticated) {
                        setAdminAuthenticated(true);
                        setShowAdmin(true);
                        localStorage.setItem('admin_mode', 'true');
                        console.log('🔧 Entrando no modo admin autenticado');
                      } else {
                        // Não autenticado - será tratado pelo useEffect quando URL mudar
                        console.log('🔐 Redirecionando para tela de login admin');
                      }
                    } else {
                      // 🔧 CORREÇÃO: Saindo do modo admin
                      window.location.hash = '';
                      setShowAdmin(false);
                      localStorage.removeItem('admin_mode');
                      console.log('🔧 Saindo do modo admin');
                    }
                  }}
                  className="flex items-center gap-2 px-3 py-1 bg-accent-warm text-primary-accent rounded text-sm hover:bg-opacity-90"
                >
                  <Settings className="h-4 w-4" />
                  {showAdmin ? 'Simulador' : 'Admin'}
                </button>
                <div>
                  <p className="text-sm text-accent-warm">Bem-vindo, {leadInfo.name}</p>
                  <button 
                    onClick={() => {
                      localStorage.removeItem('access_token');
                      localStorage.removeItem('admin_mode');
                      localStorage.removeItem('admin_authenticated'); // 🔐 Limpar autenticação admin
                      setHasAccess(false);
                      setAccessToken(null);
                      setLeadInfo(null);
                      setShowAdmin(false);
                      setAdminAuthenticated(false);
                      setAdminPassword('');
                      setAdminLoginError('');
                    }}
                    className="text-xs text-neutral-light opacity-75 hover:opacity-100"
                  >
                    Sair
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Abas Principais */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="simulador" className="flex items-center gap-2">
                <Calculator className="h-4 w-4" />
                Simulador
              </TabsTrigger>
              <TabsTrigger value="analise-contrato" className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Análise de Contrato
              </TabsTrigger>
            </TabsList>

            {/* Conteúdo das Abas */}
            <TabsContent value="simulador" className="mt-6">
              {/* Todo o conteúdo do simulador atual */}
              <div className="flex items-center gap-3 justify-between mb-4">
                <div className="flex items-center gap-3">
                  <Calculator className="h-6 w-6 text-accent-warm" />
                  <div>
                    <h2 className="text-xl font-bold">Simulador de Consórcio</h2>
                    <p className="text-neutral-light opacity-90">Análise completa de lance livre e fluxos de caixa</p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 md:gap-8">
                {/* Painel de Parâmetros */}
                <div className="lg:col-span-2">
                  <Card>
                    <CardHeader className="pb-4">
                      <CardTitle className="flex items-center gap-2">
                        <Calculator className="h-5 w-5" />
                        Parâmetros da Simulação
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Todos os campos de input do simulador */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="valorCarta" className="text-sm font-medium">Valor da Carta</Label>
                          <Input
                            id="valorCarta"
                            type="number"
                            step="1000"
                            value={parametros.valor_carta}
                            onChange={(e) => handleInputChange('valor_carta', parseFloat(e.target.value))}
                            className="mt-1"
                          />
                        </div>
                        <div>
                          <Label htmlFor="prazoMeses" className="text-sm font-medium">Prazo (meses)</Label>
                          <Input
                            id="prazoMeses"
                            type="number"
                            value={parametros.prazo_meses}
                            onChange={(e) => handleInputChange('prazo_meses', parseInt(e.target.value))}
                            className="mt-1"
                          />
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="taxaAdmin" className="text-sm font-medium">Taxa Administração (%)</Label>
                          <Input
                            id="taxaAdmin"
                            type="number"
                            step="0.01"
                            value={parametros.taxa_admin * 100}
                            onChange={(e) => handleInputChange('taxa_admin', parseFloat(e.target.value) / 100)}
                            className="mt-1"
                          />
                        </div>
                        <div>
                          <Label htmlFor="fundoReserva" className="text-sm font-medium">Fundo Reserva (%)</Label>
                          <Input
                            id="fundoReserva"
                            type="number"
                            step="0.01"
                            value={parametros.fundo_reserva * 100}
                            onChange={(e) => handleInputChange('fundo_reserva', parseFloat(e.target.value) / 100)}
                            className="mt-1"
                          />
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="mesContemplacao" className="text-sm font-medium">Mês Contemplação</Label>
                          <Input
                            id="mesContemplacao"
                            type="number"
                            value={parametros.mes_contemplacao}
                            onChange={(e) => handleInputChange('mes_contemplacao', parseInt(e.target.value))}
                            className="mt-1"
                          />
                        </div>
                        <div>
                          <Label htmlFor="lanceLivre" className="text-sm font-medium">Lance Livre (%)</Label>
                          <Input
                            id="lanceLivre"
                            type="number"
                            step="0.01"
                            value={parametros.lance_livre_perc * 100}
                            onChange={(e) => handleInputChange('lance_livre_perc', parseFloat(e.target.value) / 100)}
                            className="mt-1"
                          />
                        </div>
                      </div>
                      
                      <div>
                        <Label htmlFor="taxaReajuste" className="text-sm font-medium">Taxa Reajuste Anual (%)</Label>
                        <Input
                          id="taxaReajuste"
                          type="number"
                          step="0.01"
                          value={parametros.taxa_reajuste_anual * 100}
                          onChange={(e) => handleInputChange('taxa_reajuste_anual', parseFloat(e.target.value) / 100)}
                          className="mt-1"
                        />
                      </div>

                      <Button 
                        onClick={simularConsorcio}
                        disabled={loading}
                        className="w-full bg-accent-warm text-primary-accent hover:bg-accent-warm/90"
                      >
                        {loading ? 'Simulando...' : 'Simular Consórcio'}
                      </Button>
                    </CardContent>
                  </Card>
                </div>

                {/* Resultados */}
                <div className="lg:col-span-3 space-y-6">
                  {erro && (
                    <Card className="border-destructive">
                      <CardContent className="pt-6">
                        <div className="flex items-center gap-2 text-destructive">
                          <AlertCircle className="h-5 w-5" />
                          <span>{erro}</span>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {resultados && (
                    <>
                      {/* Métricas Principais */}
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground">CET Anual</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold text-accent-warm">
                              {resultados.resultados?.cet_anual !== undefined && resultados.resultados?.cet_anual !== null ? `${(resultados.resultados.cet_anual * 100).toFixed(2)}%` : 'N/A'}
                            </div>
                            <p className="text-sm text-muted-foreground">Custo Efetivo Total</p>
                          </CardContent>
                        </Card>
                        
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground">Valor Total</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold text-accent-warm">
                              R$ {resultados.resumo_financeiro?.total_parcelas?.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) || 'N/A'}
                            </div>
                            <p className="text-sm text-muted-foreground">Total a ser pago</p>
                          </CardContent>
                        </Card>

                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground">Parcela Após Contemplação</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold text-green-600">
                              R$ {resultados.detalhamento && resultados.detalhamento[parametros.mes_contemplacao - 1] 
                                ? resultados.detalhamento[parametros.mes_contemplacao - 1].parcela_depois?.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) 
                                : 'N/A'}
                            </div>
                            <p className="text-sm text-muted-foreground">Mês {parametros.mes_contemplacao}</p>
                          </CardContent>
                        </Card>

                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground">Última Parcela</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold text-blue-600">
                              R$ {resultados.detalhamento && resultados.detalhamento.length > 0 
                                ? resultados.detalhamento[resultados.detalhamento.length - 1].parcela_depois?.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) 
                                : 'N/A'}
                            </div>
                            <p className="text-sm text-muted-foreground">Com reajustes (Mês {parametros.prazo_meses})</p>
                          </CardContent>
                        </Card>
                      </div>

                      {/* Cards de Probabilidades */}
                      {resultados.resumo_financeiro && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                          <Card>
                            <CardHeader className="pb-2">
                              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                                <TrendingUp className="h-4 w-4" />
                                Probabilidade no Mês {parametros.mes_contemplacao}
                              </CardTitle>
                            </CardHeader>
                            <CardContent>
                              <div className="text-2xl font-bold text-purple-600">
                                {resultados.resumo_financeiro.prob_contemplacao_no_mes !== undefined 
                                  ? `${(resultados.resumo_financeiro.prob_contemplacao_no_mes * 100).toFixed(2)}%` 
                                  : 'N/A'}
                              </div>
                              <p className="text-sm text-muted-foreground">Chance de ser contemplado neste mês específico</p>
                            </CardContent>
                          </Card>

                          <Card>
                            <CardHeader className="pb-2">
                              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                                <Target className="h-4 w-4" />
                                Probabilidade até o Mês {parametros.mes_contemplacao}
                              </CardTitle>
                            </CardHeader>
                            <CardContent>
                              <div className="text-2xl font-bold text-orange-600">
                                {resultados.resumo_financeiro.prob_contemplacao_ate_mes !== undefined 
                                  ? `${(resultados.resumo_financeiro.prob_contemplacao_ate_mes * 100).toFixed(2)}%` 
                                  : 'N/A'}
                              </div>
                              <p className="text-sm text-muted-foreground">Chance acumulada de ser contemplado até este mês</p>
                            </CardContent>
                          </Card>
                        </div>
                      )}

                      {/* Gráficos */}
                      <Tabs defaultValue="probabilidade" className="w-full">
                        <TabsList className="grid w-full grid-cols-3">
                          <TabsTrigger value="probabilidade">Probabilidade</TabsTrigger>
                          <TabsTrigger value="fluxo">Fluxo de Caixa</TabsTrigger>
                          <TabsTrigger value="saldo">Saldo Devedor</TabsTrigger>
                        </TabsList>

                        <TabsContent value="probabilidade" className="space-y-4">
                          <Card>
                            <CardHeader>
                              <CardTitle className="flex items-center gap-2">
                                <TrendingUp className="h-5 w-5" />
                                Probabilidade de Contemplação
                              </CardTitle>
                            </CardHeader>
                            <CardContent>
                              {resultados.grafico_probabilidade?.labels && (
                                <div className="h-80">
                                  <Line data={resultados.grafico_probabilidade} options={chartOptions} />
                                </div>
                              )}
                            </CardContent>
                          </Card>
                        </TabsContent>

                        <TabsContent value="fluxo" className="space-y-4">
                          <Card>
                            <CardHeader>
                              <CardTitle className="flex items-center gap-2">
                                <PieChart className="h-5 w-5" />
                                Fluxo de Caixa Detalhado
                              </CardTitle>
                            </CardHeader>
                            <CardContent>
                              {resultados.detalhamento ? (
                                <div className="overflow-x-auto">
                                  <table className="w-full border-collapse border border-gray-300">
                                    <thead>
                                      <tr className="bg-gray-50">
                                        <th className="border border-gray-300 px-4 py-2 text-left">Mês</th>
                                        <th className="border border-gray-300 px-4 py-2 text-left">Data</th>
                                        <th className="border border-gray-300 px-4 py-2 text-left">Parcela</th>
                                        <th className="border border-gray-300 px-4 py-2 text-left">Valor da Carta</th>
                                        <th className="border border-gray-300 px-4 py-2 text-left">Fluxo Líquido</th>
                                        <th className="border border-gray-300 px-4 py-2 text-left">Saldo Devedor</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {/* Primeiros 24 meses */}
                                      {resultados.detalhamento.slice(0, 24).map((item, index) => (
                                        <tr key={index} className={item.eh_contemplacao ? 'bg-green-50' : ''}>
                                          <td className="border border-gray-300 px-4 py-2">{item.mes}</td>
                                          <td className="border border-gray-300 px-4 py-2">{item.data}</td>
                                          <td className="border border-gray-300 px-4 py-2">
                                            R$ {item.parcela_corrigida?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                          </td>
                                          <td className="border border-gray-300 px-4 py-2">
                                            R$ {item.valor_carta_corrigido?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                          </td>
                                          <td className={`border border-gray-300 px-4 py-2 ${item.fluxo_liquido > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                            R$ {item.fluxo_liquido?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                          </td>
                                          <td className="border border-gray-300 px-4 py-2">
                                            R$ {item.saldo_devedor?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                          </td>
                                        </tr>
                                      ))}
                                      
                                      {/* Meses anuais (36, 48, 60, etc.) */}
                                      {resultados.detalhamento.length > 24 && (
                                        <>
                                          <tr className="bg-gray-100">
                                            <td colSpan={6} className="border border-gray-300 px-4 py-2 text-center font-semibold">
                                              --- Meses Anuais ---
                                            </td>
                                          </tr>
                                          {[36, 48, 60, 72, 84, 96, 108, 120].map((mes) => {
                                            const item = resultados.detalhamento[mes - 1];
                                            if (!item) return null;
                                            return (
                                              <tr key={mes} className={item.eh_contemplacao ? 'bg-green-50' : ''}>
                                                <td className="border border-gray-300 px-4 py-2">{item.mes}</td>
                                                <td className="border border-gray-300 px-4 py-2">{item.data}</td>
                                                <td className="border border-gray-300 px-4 py-2">
                                                  R$ {item.parcela_corrigida?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                                </td>
                                                <td className="border border-gray-300 px-4 py-2">
                                                  R$ {item.valor_carta_corrigido?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                                </td>
                                                <td className={`border border-gray-300 px-4 py-2 ${item.fluxo_liquido > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                                  R$ {item.fluxo_liquido?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                                </td>
                                                <td className="border border-gray-300 px-4 py-2">
                                                  R$ {item.saldo_devedor?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                                </td>
                                              </tr>
                                            );
                                          })}
                                        </>
                                      )}
                                    </tbody>
                                  </table>
                                  
                                  <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
                                    <p className="text-sm text-blue-800">
                                      <strong>Legenda:</strong> Linha verde indica o mês de contemplação. 
                                      Fluxo positivo = recebe dinheiro, Fluxo negativo = paga parcela.
                                    </p>
                                  </div>
                                </div>
                              ) : (
                                <p className="text-gray-500">Execute uma simulação para ver o fluxo de caixa detalhado.</p>
                              )}
                            </CardContent>
                          </Card>
                        </TabsContent>

                        <TabsContent value="saldo" className="space-y-4">
                          <Card>
                            <CardHeader>
                              <CardTitle className="flex items-center gap-2">
                                <TrendingUp className="h-5 w-5" />
                                Saldo Devedor
                              </CardTitle>
                            </CardHeader>
                            <CardContent>
                              {resultados.grafico_saldo?.labels && (
                                <div className="h-80">
                                  <Line data={resultados.grafico_saldo} options={chartOptions} />
                                </div>
                              )}
                            </CardContent>
                          </Card>
                        </TabsContent>
                      </Tabs>

                      {/* Tabela de dados */}
                      {resultados.tabela_dados && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <FileText className="h-5 w-5" />
                              Dados Detalhados
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="overflow-x-auto">
                              <table className="w-full border-collapse border border-gray-300">
                                <thead>
                                  <tr className="bg-gray-50">
                                    {resultados.tabela_dados[0]?.map((header, index) => (
                                      <th key={index} className="border border-gray-300 px-4 py-2 text-left">
                                        {header}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {resultados.tabela_dados.slice(1).map((row, rowIndex) => (
                                    <tr key={rowIndex}>
                                      {row.map((cell, cellIndex) => (
                                        <td key={cellIndex} className="border border-gray-300 px-4 py-2">
                                          {cell}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </CardContent>
                        </Card>
                      )}

                      {/* Botão de download PDF */}
                      <div className="flex justify-center">
                        <Button 
                          onClick={downloadRelatorioPdf}
                          disabled={loadingPdf}
                          className="bg-primary text-primary-foreground hover:bg-primary/90"
                        >
                          {loadingPdf ? (
                            <>
                              <Loader className="mr-2 h-4 w-4 animate-spin" />
                              Gerando PDF...
                            </>
                          ) : (
                            <>
                              <Download className="mr-2 h-4 w-4" />
                              Baixar Relatório PDF
                            </>
                          )}
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </TabsContent>
            
            {/* Aba de Análise de Contrato */}
            <TabsContent value="analise-contrato" className="mt-6">
              <ContractAnalysis />
            </TabsContent>

          </Tabs>
        </div>
      )}
    </div>
  );
}

export default App;
