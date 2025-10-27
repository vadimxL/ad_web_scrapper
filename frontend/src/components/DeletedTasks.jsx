import { useContext, useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { Accordion, AccordionSummary, AccordionDetails, Box, Button, CircularProgress, Stack, Typography } from '@mui/material';
import HistoryIcon from '@mui/icons-material/History';
import ReplayIcon from '@mui/icons-material/Replay';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { AuthContext } from '../context/AuthContext';
import { fetchDeletedTasks, recreateTaskFromHistory } from '../api/client';

function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleString();
  } catch (_) {
    return dateStr;
  }
}

function DeletedTaskItem({ task, onRecreated, disabled }) {
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleRecreate = async () => {
    if (!user?.email) return;
    setLoading(true);
    setMessage('');
    setError('');
    try {
      await recreateTaskFromHistory(task, user.email);
      setMessage('Alert recreated');
      if (onRecreated) onRecreated();
    } catch (e) {
      const detail = e?.response?.data?.detail || e.message || 'Failed';
      // Common backend message when task already exists
      if (/already exists/i.test(detail)) {
        setError('Alert already exists');
      } else {
        setError(detail);
      }
    } finally {
      setLoading(false);
    }
  };

  const params = task.params || {};
  return (
    <Accordion sx={{ mb: 1 }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />}>\n        <Stack direction="row" spacing={1} alignItems="center">\n          <HistoryIcon color="disabled" fontSize="small" />\n          <Typography variant="subtitle2" sx={{ fontWeight: 500 }}>{task.title}</Typography>\n        </Stack>\n      </AccordionSummary>
      <AccordionDetails>
        <Typography variant="caption" color="text.secondary">Original ID: {task.id}</Typography>
        <Box sx={{ mt: 1 }}>
          {params.manufacturer && <Typography><strong>Manufacturer IDs:</strong> {params.manufacturer}</Typography>}
          {params.model && <Typography><strong>Model IDs:</strong> {params.model}</Typography>}
          {params.year && <Typography><strong>Years:</strong> {params.year}</Typography>}
          {params.km && <Typography><strong>KM:</strong> {params.km}</Typography>}
          {params.engineval && <Typography><strong>Engine Volume:</strong> {params.engineval}</Typography>}
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>Created: {formatDate(task.created_at)}</Typography>
        {task.deleted_at && (
          <Typography variant="caption" color="text.secondary">Deleted: {formatDate(task.deleted_at)}</Typography>
        )}
        <Button
          size="small"
            sx={{ mt: 1 }}
          variant="outlined"
          startIcon={loading ? <CircularProgress size={14} /> : <ReplayIcon fontSize="inherit" />}
          onClick={handleRecreate}
          disabled={loading || disabled}
        >
          {loading ? 'Recreating…' : 'Recreate Alert'}
        </Button>
        {(message || error) && (
          <Typography variant="caption" sx={{ mt: 0.5 }} color={error ? 'error' : 'success.main'}>
            {error || message}
          </Typography>
        )}
      </AccordionDetails>
    </Accordion>
  );
}
DeletedTaskItem.propTypes = { task: PropTypes.any, onRecreated: PropTypes.func, disabled: PropTypes.bool };

export default function DeletedTasks({ onHistoryChanged, triggerReload = 0, onRecreatedTask }) {
  const { user } = useContext(AuthContext);
  const [deleted, setDeleted] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadDeleted = async () => {
    if (!user) { setDeleted([]); return; }
    setLoading(true);
    try {
      const data = await fetchDeletedTasks();
      setDeleted(Array.isArray(data) ? data : []);
    } catch (e) {
      setDeleted([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadDeleted(); }, [user, triggerReload]);

  if (!user) return null;

  return (
    <Box sx={{ mt: 4 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1, flexWrap: 'wrap' }}>
        <HistoryIcon color="primary" fontSize="small" />
        <Typography variant="h6" gutterBottom sx={{ mb: 0 }}>Deleted Alerts History</Typography>
        {loading && <CircularProgress size={16} />}
        {deleted.length === 0 && !loading && (
          <Typography variant="caption" color="text.secondary">No deleted alerts yet.</Typography>
        )}
      </Stack>
      {deleted.map(t => (
        <DeletedTaskItem
          key={t.id}
          task={t}
          onRecreated={() => {
            if (onRecreatedTask) onRecreatedTask();
            // reload history to reflect potential duplicates removal
            loadDeleted();
          }}
          disabled={loading}
        />
      ))}
    </Box>
  );
}

DeletedTasks.propTypes = { onHistoryChanged: PropTypes.func, triggerReload: PropTypes.number, onRecreatedTask: PropTypes.func };
