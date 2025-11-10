/**
 * Utilitários de autenticação
 */

import api from './api-client';
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

/**
 * Faz login do usuário
 */
export async function login(email: string, password: string): Promise<User> {
  console.log('📡 Chamando API de login...', { email });
  const response = await api.auth.login({ email, password });
  console.log('✅ Resposta da API:', response.data);
  const tokens: AuthTokens = response.data;

  // Salvar tokens
  console.log('💾 Salvando tokens no localStorage...');
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);

  // Buscar dados do usuário com o token explícito usando axios puro
  console.log('👤 Buscando dados do usuário...');
  const userResponse = await axios.get(`${API_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${tokens.access_token}`,
    },
  });
  const user: User = userResponse.data;
  console.log('✅ Dados do usuário:', user);

  // Salvar usuário
  localStorage.setItem('user', JSON.stringify(user));

  return user;
}

/**
 * Faz registro de novo usuário
 */
export async function register(
  email: string,
  username: string,
  password: string
): Promise<User> {
  console.log('📡 Chamando API de registro...', { email, username });
  const response = await api.auth.register({ email, username, password });
  console.log('✅ Resposta da API:', response.data);
  const tokens: AuthTokens = response.data;

  // Salvar tokens
  console.log('💾 Salvando tokens no localStorage...');
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);

  // Buscar dados do usuário com o token explícito usando axios puro
  console.log('👤 Buscando dados do usuário...');
  const userResponse = await axios.get(`${API_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${tokens.access_token}`,
    },
  });
  const user: User = userResponse.data;
  console.log('✅ Dados do usuário:', user);

  // Salvar usuário
  localStorage.setItem('user', JSON.stringify(user));

  return user;
}

/**
 * Faz logout do usuário
 */
export function logout(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  window.location.href = '/login';
}

/**
 * Verifica se usuário está autenticado
 */
export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false;
  return !!localStorage.getItem('access_token');
}

/**
 * Obtém usuário atual do localStorage
 */
export function getCurrentUser(): User | null {
  if (typeof window === 'undefined') return null;

  const userStr = localStorage.getItem('user');
  if (!userStr) return null;

  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
}

/**
 * Obtém access token
 */
export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}
