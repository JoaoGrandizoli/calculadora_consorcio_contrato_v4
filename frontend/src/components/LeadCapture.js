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
    
    setShowForm(false);
    
    try {
      // 🔧 NOVA ESTRATÉGIA: Capturar email do Typeform e buscar lead por email + timestamp
      
      // Tentar extrair email do callback do Typeform
      const submittedEmail = data?.formResponse?.answers?.find(
        answer => answer.type === 'email'
      )?.email;
      
      console.log('📧 Email capturado do Typeform:', submittedEmail);
      
      const maxAttempts = 8;
      const baseDelay = 800;
      
      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        console.log(`🔍 Tentativa ${attempt}/${maxAttempts} - Buscando lead...`);
        
        try {
          const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'}/api/admin/leads`);
          const data_leads = await response.json();
          
          if (data_leads.leads && data_leads.leads.length > 0) {
            let targetLead = null;
            
            if (submittedEmail) {
              // ESTRATÉGIA A: Buscar por email exato + recente (último 5 minutos)
              const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
              
              targetLead = data_leads.leads.find(lead => 
                lead.email === submittedEmail && 
                new Date(lead.created_at) > fiveMinutesAgo
              );
              
              if (targetLead) {
                console.log('✅ Lead encontrado por EMAIL + TIMESTAMP:', targetLead.name);
              }
            }
            
            if (!targetLead) {
              // ESTRATÉGIA B: Lead mais recente (últimos 2 minutos)
              const twoMinutesAgo = new Date(Date.now() - 2 * 60 * 1000);
              
              targetLead = data_leads.leads.find(lead => {
                const leadDate = new Date(lead.created_at);
                return leadDate > twoMinutesAgo && 
                       lead.access_token && 
                       !lead.name.includes('João Silva') && 
                       !lead.name.includes('Test');
              });
              
              if (targetLead) {
                console.log('✅ Lead encontrado por TIMESTAMP:', targetLead.name);
              }
            }
            
            if (targetLead) {
              console.log('🔑 Usando token:', targetLead.access_token);
              
              // Salvar dados
              localStorage.setItem('access_token', targetLead.access_token);
              localStorage.setItem('lead_data', JSON.stringify({
                leadId: targetLead.id,
                name: targetLead.name,
                email: targetLead.email,
                token: targetLead.access_token,
                timestamp: new Date().toISOString()
              }));
              
              onAccessGranted(targetLead.access_token);
              return;
            }
          }
          
          // Aguardar próxima tentativa
          if (attempt < maxAttempts) {
            const delay = baseDelay * attempt; // Delay progressivo
            await new Promise(resolve => setTimeout(resolve, delay));
          }
          
        } catch (fetchError) {
          console.log(`⚠️ Erro na tentativa ${attempt}:`, fetchError.message);
          if (attempt < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, baseDelay * attempt));
          }
        }
      }
      
      // Se chegou aqui, não encontrou
      console.log('❌ Não encontrou lead após todas as tentativas');
      const fallbackToken = 'fallback-' + Date.now();
      localStorage.setItem('access_token', fallbackToken);
      onAccessGranted(fallbackToken);
      
    } catch (error) {
      console.error('❌ Erro na sincronização:', error);
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