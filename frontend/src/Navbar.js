import React, { useState } from 'react';
import { Link } from "react-router-dom";
import './Navbar.css';
import { Logout } from "@mui/icons-material";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import { useAuth } from "./context/AuthContext";
import AuthPanel from "./components/AuthPanel";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";

function Navbar() {
    const { user, logout } = useAuth();
    const [open, setOpen] = useState(false);
    const [mode, setMode] = useState('login');

    const handleOpen = (m) => {
        setMode(m);
        setOpen(true);
    };
    const handleClose = () => setOpen(false);

    return (
        <>
            <AppBar position="static" color="default" elevation={1} sx={{ px: 2 }}>
                <Toolbar sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', minHeight: 56, py: 0 }}>
                    <Box component={Link} to="/" sx={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}>
                        <Box component="img" src="/logo.svg" alt="Logo" sx={{ height: 32, width: 'auto', mr: 2 }} />
                        {/* Optional title text: remove if not needed */}
                        {/* <Typography variant="h6" color="inherit" sx={{ display: { xs: 'none', sm: 'block' } }}>CarAlert</Typography> */}
                    </Box>
                    {user ? (
                        <Stack direction="row" spacing={2} alignItems="center">
                            <Typography variant="body2" noWrap>{user.email}</Typography>
                            <Tooltip title="Logout">
                                <IconButton color="inherit" size="small" onClick={logout} sx={{ m: 0 }}>
                                    <Logout fontSize="small" />
                                </IconButton>
                            </Tooltip>
                        </Stack>
                    ) : (
                        <Stack direction="row" spacing={1}>
                            <Button color="inherit" onClick={() => handleOpen('login')}>Login</Button>
                            <Button variant="contained" onClick={() => handleOpen('register')}>Register</Button>
                        </Stack>
                    )}
                </Toolbar>
            </AppBar>

            <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
                <DialogTitle>{mode === 'login' ? 'Login' : 'Register'}</DialogTitle>
                <DialogContent>
                    <AuthPanel initialMode={mode} />
                </DialogContent>
            </Dialog>
        </>
    );
}

export default Navbar;
