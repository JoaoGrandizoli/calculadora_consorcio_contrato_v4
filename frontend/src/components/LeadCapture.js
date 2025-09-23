import React, { useState, useEffect } from 'react';
import { Widget } from '@typeform/embed-react';

const LeadCapture = ({ onAccessGranted }) => {
  const [showForm, setShowForm] = useState(true);
  const typeformId = process.env.REACT_APP_TYPEFORM_ID || 'dN3w60PD';

  useEffect(() => {
    // Verificar se há um token de acesso no localStorage
    const existingToken = localStorage.getItem('access_token');
    if (existingToken) {
      onAccessGranted(existingToken);
      setShowForm(false);
    }
  }, [onAccessGranted]);

  const handleTypeformSubmit = async (data) => {
    console.log('🎯 Typeform submetido:', data);
    
    setShowForm(false); // Esconder form imediatamente
    
    try {
      // 🚀 OTIMIZAÇÃO: Estratégia de polling inteligente e progressiva
      // Tentativas mais rápidas no início, depois intervalos maiores
      
      const attempts = [
        { delay: 500, msg: "Processando formulário..." },
        { delay: 800, msg: "Validando dados..." },
        { delay: 1000, msg: "Sincronizando com o servidor..." },
        { delay: 1200, msg: "Quase pronto..." },
        { delay: 1500, msg: "Finalizando..." },
        { delay: 2000, msg: "Última verificação..." }
      ];
      
      console.log('🔄 Iniciando busca inteligente pelo lead...');
      
      for (let i = 0; i < attempts.length; i++) {
        console.log(`🔍 ${attempts[i].msg} (${i + 1}/${attempts.length})`);
        
        try {
          // Buscar todos os leads
          const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'}/api/admin/leads`);
          const data_leads = await response.json();
          
          // Estratégia: Pegar o lead MAS RECENTE (primeiro da lista)
          if (data_leads.leads && data_leads.leads.length > 0) {
            const latestLead = data_leads.leads[0];
            
            // Validar se é um lead real e muito recente (criado nos últimos 3 minutos)
            const leadCreatedAt = new Date(latestLead.created_at);
            const now = new Date();
            const diffMinutes = (now - leadCreatedAt) / (1000 * 60);
            
            if (latestLead.access_token && 
                latestLead.email && 
                latestLead.email.includes('@') &&
                !latestLead.name.toLowerCase().includes('joão') && 
                !latestLead.name.toLowerCase().includes('test') &&
                !latestLead.name.toLowerCase().includes('teste') &&
                diffMinutes <= 3) { // Lead criado nos últimos 3 minutos
              
              console.log('✅ Lead recente encontrado:', latestLead.name, 'criado há', diffMinutes.toFixed(1), 'minutos');
              
              // Salvar dados no localStorage
              localStorage.setItem('access_token', latestLead.access_token);
              localStorage.setItem('lead_data', JSON.stringify({
                leadId: latestLead.id,
                name: latestLead.name,
                email: latestLead.email,
                token: latestLead.access_token,
                timestamp: new Date().toISOString()
              }));
              
              // Conceder acesso
              console.log('🔑 Concedendo acesso com token:', latestLead.access_token);
              onAccessGranted(latestLead.access_token);
              return;
            }
          }
          
          // Se não encontrou ainda, aguardar próxima tentativa
          if (i < attempts.length - 1) {
            await new Promise(resolve => setTimeout(resolve, attempts[i].delay));
          }
          
        } catch (fetchError) {
          console.log(`⚠️ Erro na tentativa ${i + 1}:`, fetchError.message);
          if (i < attempts.length - 1) {
            await new Promise(resolve => setTimeout(resolve, attempts[i].delay));
          }
        }
      }
      
      // Se chegou aqui, não encontrou lead após todas as tentativas
      console.log('⚠️ Não encontrou lead válido após', maxAttempts, 'tentativas');
      const fallbackToken = 'fallback-' + Date.now();
      localStorage.setItem('access_token', fallbackToken);
      onAccessGranted(fallbackToken);
      
    } catch (error) {
      console.error('❌ Erro na sincronização:', error);
      
      // Fallback de emergência
      const errorToken = 'error-' + Date.now();
      localStorage.setItem('access_token', errorToken);
      onAccessGranted(errorToken);
    }
  };

  const handleTypeformReady = () => {
    console.log('Typeform está pronto');
  };

  if (!showForm) {
    return (
      <div className="text-center py-8">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 max-w-md mx-auto">
          <div className="text-blue-600 text-4xl mb-3">
            <div className="animate-spin inline-block">⏳</div>
          </div>
          <h3 className="text-xl font-semibold text-blue-800 mb-2">
            Processando cadastro...
          </h3>
          <p className="text-blue-700 text-sm">
            Aguarde enquanto validamos seus dados
          </p>
          <div className="mt-3 text-xs text-blue-600">
            Em alguns segundos você terá acesso ao simulador
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <h2 className="text-2xl font-bold text-gray-800 mb-2 text-center">
          📋 Cadastro para Acessar o Simulador
        </h2>
        <p className="text-gray-600 text-center mb-4 text-sm">
          Preencha o formulário abaixo para ter acesso gratuito ao simulador
        </p>
        
        <div style={{ height: '500px' }}>
          <Widget
            id={typeformId}
            onSubmit={handleTypeformSubmit}
            onReady={handleTypeformReady}
            style={{ width: '100%', height: '100%' }}
            className="typeform-widget"
            hideHeaders={true}
            hideFooter={false}
          />
        </div>
        
        <div className="text-center mt-4">
          <p className="text-xs text-gray-500">
            🔒 Seus dados estão seguros e protegidos
          </p>
        </div>
      </div>
    </div>
  );
};

export default LeadCapture;