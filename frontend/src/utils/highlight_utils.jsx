import React from 'react';

/**
 * Highlights exact keyword matches inside a paragraph of text.
 * @param {string} text The full review text.
 * @param {string} keywordsString A string of keywords (e.g., "login, crash, app")
 * @returns {Array} An array of React elements with highlighted spans.
 */
export const highlightEntities = (text, keywordsString) => {
    if (!text) return text;
    if (!keywordsString || typeof keywordsString !== 'string') return text;

    // 1. Clean and prepare keywords
    // Keywords from NMF usually come in comma-separated strings
    const rawKeywords = keywordsString.split(',').map(kw => kw.trim().toLowerCase()).filter(kw => kw.length > 2);
    
    if (rawKeywords.length === 0) return text;

    // 2. Build a regex to match any of the keywords (case-insensitive)
    // Escape keywords to prevent regex injection
    const escapedKeywords = rawKeywords.map(kw => kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    const regexPattern = new RegExp(`(${escapedKeywords.join('|')})`, 'gi');

    // 3. Split the text, capturing the delimiters (the keywords)
    const parts = text.split(regexPattern);

    // 4. Map parts to React elements, wrapping matches in a styled span
    return parts.map((part, i) => {
        if (regexPattern.test(part)) {
            // Reset regex state since .test() advances the index with 'g' flag
            regexPattern.lastIndex = 0; 
            return (
                <span 
                    key={i} 
                    style={{ 
                        backgroundColor: 'rgba(229, 9, 20, 0.2)', // SignalShift Red transparent
                        color: '#ff4d4d',
                        padding: '1px 3px',
                        borderRadius: '3px',
                        fontWeight: 'bold',
                        border: '1px solid rgba(229, 9, 20, 0.4)'
                    }}
                >
                    {part}
                </span>
            );
        }
        return <React.Fragment key={i}>{part}</React.Fragment>;
    });
};
