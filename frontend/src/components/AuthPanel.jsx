import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import InputAdornment from '@mui/material/InputAdornment';
import IconButton from '@mui/material/IconButton';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';

const AuthPanel = ({ initialMode = 'login' }) => {
  const { user, loading, login, register, logout } = useAuth();
  const [mode, setMode] = useState(initialMode); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    setMode(initialMode);
  }, [initialMode]);

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      if (mode === 'login') {
        await login({ email, password });
      } else {
        await register({ email, password });
      }
      setEmail('');
      setPassword('');
    } catch (e) {
      setErr(e?.response?.data?.detail || 'Something went wrong');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ mb: 2 }}>
        <Typography variant="body2" color="text.secondary">Checking session…</Typography>
      </Box>
    );
  }

  if (user) {
    return (
      <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
          <div>
            <Typography variant="subtitle2" color="text.secondary">Signed in as</Typography>
            <Typography variant="h6">{user.email}</Typography>
          </div>
          <Button variant="outlined" onClick={logout}>Logout</Button>
        </Stack>
      </Paper>
    );
  }

  return (
    <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        <Button
          size="small"
          variant={mode === 'login' ? 'contained' : 'text'}
          onClick={() => setMode('login')}
        >
          Login
        </Button>
        <Button
          size="small"
          variant={mode === 'register' ? 'contained' : 'text'}
          onClick={() => setMode('register')}
        >
          Register
        </Button>
      </Stack>

      <Box component="form" onSubmit={onSubmit}>
        <Stack spacing={2}>
          <TextField
            label="Email"
            type="email"
            required
            size="small"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
          <TextField
            label="Password"
            type={showPassword ? 'text' : 'password'}
            required
            size="small"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    onClick={() => setShowPassword((show) => !show)}
                    edge="end"
                    size="small"
                  >
                    {showPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
          {err && <Typography color="error" variant="body2">{err}</Typography>}
          <Button type="submit" variant="contained" disabled={busy}>
            {busy ? 'Please wait…' : mode === 'login' ? 'Login' : 'Create account'}
          </Button>
        </Stack>
      </Box>
    </Paper>
  );
};

export default AuthPanel;
