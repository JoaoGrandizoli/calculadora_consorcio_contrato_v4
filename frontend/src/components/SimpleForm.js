import React, { useState } from 'react';
import axios from 'axios';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';

const API = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const SimpleForm = ({ onAccessGranted }) => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Gerar access token
      const accessToken = 'lead-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
      
      // Salvar lead no backend
      const leadData = {
        id: accessToken,
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        access_token: accessToken,
        has_access: true
      };
      
      // Salvar no localStorage para uso imediato
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('user_data', JSON.stringify(formData));
      
      // Tentar salvar no backend (não bloquear se falhar)
      try {
        await axios.post(`${API}/api/save-lead`, leadData);
        console.log('Lead salvo no backend');
      } catch (error) {
        console.error('Erro ao salvar lead:', error);
        // Continua mesmo se o backend falhar
      }
      
      // Liberar acesso
      onAccessGranted(accessToken);
      
    } catch (error) {
      console.error('Erro geral:', error);
      // Em caso de erro, ainda libera o acesso
      const fallbackToken = 'fallback-' + Date.now();
      localStorage.setItem('access_token', fallbackToken);
      onAccessGranted(fallbackToken);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
        <h2 className="text-2xl font-bold text-gray-800 mb-2 text-center">
          📋 Cadastro Rápido
        </h2>
        <p className="text-gray-600 text-center mb-6 text-sm">
          3 campos simples para acessar o simulador gratuitamente
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="name" className="text-sm font-medium text-gray-700">
              Nome completo *
            </Label>
            <Input
              id="name"
              type="text"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="Seu nome completo"
              required
              className="mt-1"
              disabled={isSubmitting}
            />
          </div>

          <div>
            <Label htmlFor="email" className="text-sm font-medium text-gray-700">
              E-mail *
            </Label>
            <Input
              id="email"
              type="email"
              value={formData.email}
              onChange={(e) => handleChange('email', e.target.value)}
              placeholder="seu@email.com"
              required
              className="mt-1"
              disabled={isSubmitting}
            />
          </div>

          <div>
            <Label htmlFor="phone" className="text-sm font-medium text-gray-700">
              Telefone *
            </Label>
            <Input
              id="phone"
              type="tel"
              value={formData.phone}
              onChange={(e) => handleChange('phone', e.target.value)}
              placeholder="(11) 99999-9999"
              required
              className="mt-1"
              disabled={isSubmitting}
            />
          </div>

          <Button 
            type="submit" 
            disabled={isSubmitting}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 mt-6"
          >
            {isSubmitting ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Processando...
              </div>
            ) : (
              '🚀 Acessar Simulador'
            )}
          </Button>
        </form>

        <p className="text-xs text-gray-500 text-center mt-4">
          🔒 Dados seguros e privados
        </p>
      </div>
    </div>
  );
};

export default SimpleForm;