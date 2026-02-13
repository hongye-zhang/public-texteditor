import App from './App.svelte';
import './styles/app.css';

const target = document.getElementById('app');
if (!target) {
  throw new Error('Could not find app element');
}

const app = new App({
  target
});

export default app;
