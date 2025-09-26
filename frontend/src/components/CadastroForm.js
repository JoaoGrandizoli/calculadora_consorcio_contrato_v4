import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';

const CadastroForm = ({ onAccessGranted }) => {
  const [formData, setFormData] = useState({
    nome: '',
    sobrenome: '',
    email: '',
    telefone: '',
    profissao: ''
  });

  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Limpar erro do campo quando usuário começar a digitar
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.nome.trim()) {
      newErrors.nome = 'Nome é obrigatório';
    }

    if (!formData.sobrenome.trim()) {
      newErrors.sobrenome = 'Sobrenome é obrigatório';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email é obrigatório';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Email inválido';
    }

    if (!formData.telefone.trim()) {
      newErrors.telefone = 'Telefone é obrigatório';
    } else if (formData.telefone.replace(/\D/g, '').length < 10) {
      newErrors.telefone = 'Telefone deve ter pelo menos 10 dígitos';
    }

    if (!formData.profissao.trim()) {
      newErrors.profissao = 'Profissão é obrigatória';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      // Fazer chamada para criar lead
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/criar-lead`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        throw new Error('Erro ao criar cadastro');
      }

      const result = await response.json();
      
      console.log('✅ Cadastro criado com sucesso:', result);
      
      // Salvar dados do lead
      if (result.access_token) {
        localStorage.setItem('access_token', result.access_token);
        localStorage.setItem('lead_data', JSON.stringify({
          leadId: result.lead_id,
          name: `${formData.nome} ${formData.sobrenome}`,
          email: formData.email,
          token: result.access_token,
          timestamp: new Date().toISOString(),
          source: 'custom_form'
        }));

        // Conceder acesso ao simulador
        onAccessGranted(result.access_token);
      } else {
        throw new Error('Token de acesso não recebido');
      }

    } catch (error) {
      console.error('❌ Erro ao criar cadastro:', error);
      setErrors({
        submit: 'Erro ao criar cadastro. Tente novamente.'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto bg-white p-8 rounded-lg shadow-lg">
      <div className="text-center mb-8">
        <div className="mx-auto h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
          <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Cadastro para Acessar o Simulador
        </h2>
        <p className="text-gray-600">
          Preencha seus dados para começar a simular seu consórcio
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="nome" className="block text-sm font-medium text-gray-700 mb-2">
              Nome *
            </Label>
            <Input
              id="nome"
              name="nome"
              type="text"
              value={formData.nome}
              onChange={handleInputChange}
              className={`w-full ${errors.nome ? 'border-red-500' : ''}`}
              placeholder="Seu nome"
              disabled={loading}
            />
            {errors.nome && <p className="mt-1 text-sm text-red-600">{errors.nome}</p>}
          </div>

          <div>
            <Label htmlFor="sobrenome" className="block text-sm font-medium text-gray-700 mb-2">
              Sobrenome *
            </Label>
            <Input
              id="sobrenome"
              name="sobrenome"
              type="text"
              value={formData.sobrenome}
              onChange={handleInputChange}
              className={`w-full ${errors.sobrenome ? 'border-red-500' : ''}`}
              placeholder="Seu sobrenome"
              disabled={loading}
            />
            {errors.sobrenome && <p className="mt-1 text-sm text-red-600">{errors.sobrenome}</p>}
          </div>
        </div>

        <div>
          <Label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
            Email *
          </Label>
          <Input
            id="email"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleInputChange}
            className={`w-full ${errors.email ? 'border-red-500' : ''}`}
            placeholder="seu@email.com"
            disabled={loading}
          />
          {errors.email && <p className="mt-1 text-sm text-red-600">{errors.email}</p>}
        </div>

        <div>
          <Label htmlFor="telefone" className="block text-sm font-medium text-gray-700 mb-2">
            Telefone *
          </Label>
          <Input
            id="telefone"
            name="telefone"
            type="tel"
            value={formData.telefone}
            onChange={handleInputChange}
            className={`w-full ${errors.telefone ? 'border-red-500' : ''}`}
            placeholder="(11) 99999-9999"
            disabled={loading}
          />
          {errors.telefone && <p className="mt-1 text-sm text-red-600">{errors.telefone}</p>}
        </div>

        <div>
          <Label htmlFor="profissao" className="block text-sm font-medium text-gray-700 mb-2">
            Profissão *
          </Label>
          <Input
            id="profissao"
            name="profissao"
            type="text"
            value={formData.profissao}
            onChange={handleInputChange}
            className={`w-full ${errors.profissao ? 'border-red-500' : ''}`}
            placeholder="Sua profissão"
            disabled={loading}
          />
          {errors.profissao && <p className="mt-1 text-sm text-red-600">{errors.profissao}</p>}
        </div>

        {errors.submit && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-sm text-red-600">{errors.submit}</p>
          </div>
        )}

        <Button
          type="submit"
          className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 px-4 rounded-md font-medium"
          disabled={loading}
        >
          {loading ? (
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Criando cadastro...
            </div>
          ) : (
            'Acessar Simulador'
          )}
        </Button>
      </form>

      <div className="mt-6 text-center text-xs text-gray-500">
        <p>Seus dados são seguros e serão usados apenas para o simulador</p>
      </div>
    </div>
  );
};

export default CadastroForm;