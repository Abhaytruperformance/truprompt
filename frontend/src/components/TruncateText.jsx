const TruncateText = ({ text, wordLimit = 7 }) => {

    if (typeof text !== 'string') return ""; // Ensure text is a string
    const words = text.split(' ');

    if (words.length > wordLimit) {
        return words.slice(0, wordLimit).join(' ') + '...';
    }
    return text;
}

export default TruncateText;