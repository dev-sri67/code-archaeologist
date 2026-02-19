import { formatDistanceToNow, format } from 'date-fns';

/**
 * Format file size
 * @param {number} bytes
 * @returns {string}
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Format number with K/M suffix
 * @param {number} num
 * @returns {string}
 */
export function formatNumber(num) {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
}

/**
 * Format date to human readable string
 * @param {string|Date} date
 * @returns {string}
 */
export function formatDate(date) {
  const d = typeof date === 'string' ? new Date(date) : date;
  return format(d, 'MMM d, yyyy HH:mm');
}

/**
 * Get time ago string
 * @param {string|Date} date
 * @returns {string}
 */
export function timeAgo(date) {
  const d = typeof date === 'string' ? new Date(date) : date;
  return formatDistanceToNow(d, { addSuffix: true });
}

/**
 * Get status color class
 * @param {string} status
 * @returns {string}
 */
export function getStatusColor(status) {
  const colors = {
    pending: 'text-yellow-500',
    cloning: 'text-blue-500',
    analyzing: 'text-purple-500',
    indexing: 'text-orange-500',
    completed: 'text-green-500',
    failed: 'text-red-500',
  };
  return colors[status] || 'text-gray-500';
}

/**
 * Get status background color class
 * @param {string} status
 * @returns {string}
 */
export function getStatusBgColor(status) {
  const colors = {
    pending: 'bg-yellow-100 text-yellow-800',
    cloning: 'bg-blue-100 text-blue-800',
    analyzing: 'bg-purple-100 text-purple-800',
    indexing: 'bg-orange-100 text-orange-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}

/**
 * Get language color
 * @param {string} language
 * @returns {string}
 */
export function getLanguageColor(language) {
  const colors = {
    typescript: '#3178c6',
    javascript: '#f7df1e',
    python: '#3776ab',
    java: '#b07219',
    go: '#00add8',
    rust: '#dea584',
    cpp: '#f34b7d',
    c: '#555555',
    csharp: '#178600',
    ruby: '#701516',
    php: '#4F5D95',
    swift: '#ffac45',
    kotlin: '#A97BFF',
    html: '#e34c26',
    css: '#563d7c',
    json: '#292929',
    yaml: '#cb171e',
    markdown: '#083fa1',
    dockerfile: '#384d54',
    shell: '#89e051',
  };
  return colors[language?.toLowerCase()] || '#8b949e';
}

/**
 * Get language icon name
 * @param {string} language
 * @returns {string}
 */
export function getLanguageIcon(language) {
  const icons = {
    typescript: 'TypeScript',
    javascript: 'JavaScript',
    python: 'Python',
    java: 'Java',
    go: 'Go',
    rust: 'Rust',
    cpp: 'C++',
    c: 'C',
    csharp: 'C#',
    ruby: 'Ruby',
    php: 'PHP',
    swift: 'Swift',
    kotlin: 'Kotlin',
    html: 'HTML',
    css: 'CSS',
    json: 'JSON',
    yaml: 'YAML',
    markdown: 'Markdown',
    dockerfile: 'Docker',
    shell: 'Shell',
  };
  return icons[language?.toLowerCase()] || 'File';
}

/**
 * Truncate text to max length
 * @param {string} text
 * @param {number} maxLength
 * @returns {string}
 */
export function truncateText(text, maxLength) {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

/**
 * Clean URL for display
 * @param {string} url
 * @returns {string}
 */
export function cleanUrl(url) {
  return url
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .replace(/\/$/, '');
}
