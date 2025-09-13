import {useContext, useEffect, useState} from "react";
import {Accordion, AccordionDetails, AccordionSummary} from "@mui/material";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import Container from "@mui/material/Container";
import {createTheme, ThemeProvider} from "@mui/material/styles";
import * as PropTypes from "prop-types";
import { AuthContext } from "../context/AuthContext";
import Box from "@mui/material/Box";
import { api } from "../api/client";
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import Stack from '@mui/material/Stack';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CircularProgress from '@mui/material/CircularProgress';


function ArrowDownwardIcon() { return null; }

function DeleteTask({id, onDeleted}) {
    const deleteTodo = async () => {
        try {
            await api.delete(`/tasks/${id}`);
            if (onDeleted) onDeleted();
        } catch (_) { /* ignore */ }
    };
    return (
        <Button size="small" onClick={deleteTodo}>Delete Task</Button>
    );
}

function Price(params) {
    if ("price" in params) {
        return (
            <div>
                <Typography color="primary">Price Range:</Typography>
                <Typography> {params.price} </Typography>
            </div>
        );
    }
    return null;
}

function Task({ task }) {
    return (
        <Accordion>
            <AccordionSummary expandIcon={<ArrowDownwardIcon/>}>
                <Typography>{"id: " + task.id}</Typography>
            </AccordionSummary>
            <AccordionDetails>
                <Typography color="primary">Manufacturers:</Typography>
                <Typography> {task.manufacturers} </Typography>
                <Typography color="primary">Models:</Typography>
                <Typography> {task.car_models} </Typography>
                <Typography color="primary">Submodels:</Typography>
                <Typography> {task.car_submodels} </Typography>
                <Typography color="primary">Mail:</Typography>
                <Typography> {task.mail} </Typography>
                <Price params={task.params}/>
                <DeleteTask id={task.id} />
            </AccordionDetails>
        </Accordion>
    );
}
Task.propTypes = { task: PropTypes.any };

export default function Tasks({ embedded = true }) {
    const [tasks, setTasks] = useState([]);
    const [running, setRunning] = useState(false);
    const [runMessage, setRunMessage] = useState('');
    const { user } = useContext(AuthContext);

    const fetchTasks = () => {
        api.get("/tasks")
            .then(r => setTasks(r.data))
            .catch(() => setTasks([]));
    };
    const runAll = async () => {
        setRunning(true);
        setRunMessage('');
        try {
            await api.get('/run');
            setRunMessage('Alerts execution triggered');
            // Give backend a moment, then refresh
            setTimeout(fetchTasks, 1500);
        } catch (e) {
            setRunMessage(e?.response?.data?.detail || 'Failed to trigger run');
        } finally {
            setRunning(false);
        }
    };

    useEffect(() => {
        if (user) fetchTasks(); else setTasks([]);
    }, [user]);

    const defaultTheme = createTheme();

    if (!user) {
        // When embedded, parent already shows auth UI; just hint.
        return embedded ? (
            <Typography sx={{ mt: 2 }} color="text.secondary">
                Login to see your tasks.
            </Typography>
        ) : (
            <ThemeProvider theme={defaultTheme}>
                <Container component="main" maxWidth="xs">
                    <Typography sx={{ mt: 2 }} color="text.secondary">
                        Login to see your tasks.
                    </Typography>
                </Container>
            </ThemeProvider>
        );
    }

    const content = (
        <Box sx={{ mt: 4 }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1, flexWrap: 'wrap' }}>
                <NotificationsActiveIcon color="primary" fontSize="small" />
                <Typography variant="h6" gutterBottom sx={{ mb: 0 }}>Alerts</Typography>
                <Button
                    size="small"
                    variant="outlined"
                    startIcon={running ? <CircularProgress size={14} /> : <PlayArrowIcon fontSize="inherit" />}
                    onClick={runAll}
                    disabled={running || tasks.length === 0}
                >
                    {running ? 'Running…' : 'Run Alerts'}
                </Button>
                {runMessage && <Typography variant="caption" color="text.secondary">{runMessage}</Typography>}
            </Stack>
            {tasks.length === 0 && (
                <Typography color="text.secondary">No tasks yet.</Typography>
            )}
            {tasks.map(t => <Task key={t.id} task={t} />)}
        </Box>
    );

    if (embedded) return content;

    return (
        <ThemeProvider theme={defaultTheme}>
            <Container component="main" maxWidth="xs">
                {content}
            </Container>
        </ThemeProvider>
    );
}

Tasks.propTypes = { embedded: PropTypes.bool };
