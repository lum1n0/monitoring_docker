// front/src/pages/Login.jsx (новый файл - полный)
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../api/services';

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { token } = await login(username, password);
      localStorage.setItem('token', token);
      navigate('/', { replace: true });
    } catch (err) {
      setError('Неверная почта или пароль');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: '#0b1220' }}>
      <form
        onSubmit={onSubmit}
        style={{
          width: 360,
          padding: 24,
          borderRadius: 12,
          background: '#111827',
          color: '#e5e7eb',
          boxShadow: '0 10px 20px rgba(0,0,0,0.4)',
        }}
      >
        <h2 style={{ margin: 0, marginBottom: 16, textAlign: 'center' }}>Вход</h2>

        <label style={{ display: 'block', fontSize: 14, marginBottom: 6 }}>Почта (username)</label>
        <input
          type="email"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="admin@gmail.com"
          required
          style={{
            width: '100%',
            padding: '10px 12px',
            borderRadius: 8,
            border: '1px solid #374151',
            background: '#0f172a',
            color: '#e5e7eb',
            marginBottom: 12,
          }}
        />

        <label style={{ display: 'block', fontSize: 14, marginBottom: 6 }}>Пароль</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Пароль"
          required
          style={{
            width: '100%',
            padding: '10px 12px',
            borderRadius: 8,
            border: '1px solid #374151',
            background: '#0f172a',
            color: '#e5e7eb',
            marginBottom: 16,
          }}
        />

        {error && (
          <div style={{ color: '#fca5a5', fontSize: 14, marginBottom: 12 }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            padding: '10px 12px',
            borderRadius: 8,
            background: '#2563eb',
            color: '#fff',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          {loading ? 'Входим…' : 'Войти'}
        </button>
      </form>
    </div>
  );
}
