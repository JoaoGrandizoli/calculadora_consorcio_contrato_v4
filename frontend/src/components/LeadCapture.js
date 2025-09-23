import React, { useState } from 'react';
import { Widget } from '@typeform/embed-react';

const LeadCapture = ({ onAccessGranted }) => {
  const [showForm, setShowForm] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  const handleFormSubmit = async (event) => {
    console.log('Typeform submitted:', event);
    setIsLoading(true);
    
    // Gerar access token simples
    const accessToken = 'lead-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    
    // Simular delay de processamento
    setTimeout(() => {
      localStorage.setItem('access_token', accessToken);
      onAccessGranted(accessToken);
      setShowForm(false);
      setIsLoading(false);
    }, 1500);
  };

  if (!showForm) {
    return (
      <div className="text-center py-8">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 max-w-md mx-auto">
          <div className="text-green-600 text-4xl mb-3">✅</div>
          <h3 className="text-xl font-semibold text-green-800 mb-2">
            Perfeito!
          </h3>
          <p className="text-green-700">
            Agora você pode usar o simulador de consórcio.
          </p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Processando...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-3 text-center">
          📋 Cadastro Rápido
        </h2>
        <p className="text-gray-600 text-center mb-4">
          Preencha o formulário abaixo para acessar o simulador de consórcio gratuitamente.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div style={{ height: '600px' }}>
          {process.env.REACT_APP_TYPEFORM_ID && process.env.REACT_APP_TYPEFORM_ID !== 'SEU_TYPEFORM_ID_AQUI' ? (
            <Widget
              id={process.env.REACT_APP_TYPEFORM_ID}
              style={{ width: '100%', height: '100%' }}
              className="typeform-widget"
              onSubmit={handleFormSubmit}
              onReady={() => console.log('Typeform carregado')}
            />
          ) : (
            <div className="flex items-center justify-center h-full bg-gray-50">
              <div className="text-center p-8">
                <h3 className="text-xl font-semibold text-gray-800 mb-4">
                  🔧 Configure seu Typeform
                </h3>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                  <p className="text-blue-800 text-sm mb-2">
                    <strong>Para ativar:</strong>
                  </p>
                  <ol className="text-blue-700 text-sm text-left space-y-1">
                    <li>1. Copie o ID do seu Typeform</li>
                    <li>2. Cole em: <code className="bg-blue-100 px-1 rounded">REACT_APP_TYPEFORM_ID</code></li>
                    <li>3. Reinicie o frontend</li>
                  </ol>
                </div>
                
                <p className="text-gray-600 text-sm mb-4">
                  Enquanto isso, você pode pular para testar:
                </p>
                
                <button 
                  onClick={() => {
                    const mockAccessToken = 'demo-' + Date.now();
                    localStorage.setItem('access_token', mockAccessToken);
                    onAccessGranted(mockAccessToken);
                    setShowForm(false);
                  }}
                  className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 transition-colors"
                >
                  🚀 Pular e Testar
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 text-center text-sm text-gray-500">
        <p>🔒 Dados seguros e privados</p>
      </div>
    </div>
  );
};

export default LeadCapture;