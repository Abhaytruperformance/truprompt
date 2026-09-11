import React, { useRef, useState } from 'react';
import AISubmit from '../assets/AISubmit.svg'
import Arrow from '../assets/accordionIcon.svg'

import { useDispatch, useSelector } from 'react-redux';
import { handlePromptSearch, extractFromFile, extractFromUrl } from './openAIUtils';
import Swal from 'sweetalert2';
import '@sweetalert2/theme-dark';
import { selectIsDropdownOpen, setIsDropdownOpen, setMainComponent, setPromptSource } from '../store/slices/truPromptSlice';
import { useGetModelsQuery } from '../store/slices/orgSlice';


const HandlePrompt = ({
    prompt,
    setPrompt,
    setLoading,
    selectedOptions,
    setSelectedOptions,
    openAIResults,
    setOpenAIResults,
    // dropdownRef,
}) => {


    const dispatch = useDispatch();

    const isDropdownOpen = useSelector(selectIsDropdownOpen)

    // const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const dropdownRef = useRef(null);
    // const [prompt, setPrompt] = useState("");

    // useEffect(() => {
    //     if (isDropdownOpen) {
    //         setIsBlur(!isBlur)
    //     }
    // }, [isDropdownOpen, isBlur, setIsBlur])


    const optionsList = [
        { name: "SEO", param: "As an SEO expert, focus on tasks like on-page optimization (meta tags, content structure), off-page strategies (backlink building, outreach), and performing a comprehensive site audit to identify issues and opportunities" },
        { name: "Design", param: "As a designer, consider aspects such as user experience, visual aesthetics, brand consistency, and effective communication through design elements" },
        { name: "Communication", param: "As a communication specialist, focus on effective messaging, audience engagement, and strategies for clear and impactful communication across various channels" },
        { name: "Web Development", param: "As a web developer, consider aspects such as responsive design, performance optimization, accessibility, and modern web technologies" },
        { name: "Lead Generation", param: "As a lead generation expert, focus on strategies to attract and convert potential customers into qualified leads for the business" },
        { name: "Lifecycle Marketing", param: "As a lifecycle marketing specialist, focus on strategies for customer acquisition, retention, and growth across various stages of the customer journey" },
        { name: "Business Development", param: "As a business development professional, focus on strategies for growth, partnerships, market expansion, and improving overall business performance" },
    ];

    const [otherChecked, setOtherChecked] = useState(false);
    const [customOption, setCustomOption] = useState('');

    const { data: models = [] } = useGetModelsQuery();
    const [selectedModel, setSelectedModel] = useState(null);
    const activeModel = selectedModel || models[0]?.id || null;

    const [showContextInput, setShowContextInput] = useState(false);
    const [urlInput, setUrlInput] = useState('');
    const [contextLoading, setContextLoading] = useState(false);
    const [contextData, setContextData] = useState(null); // { text, characters, truncated, warning, sourceType, sourceName }
    const [showContextPreview, setShowContextPreview] = useState(false);

    const showContextError = (err) => {
        Swal.fire({
            title: 'Could not extract content',
            text: err?.message || 'Please try a different file or URL.',
            icon: 'error',
            confirmButtonText: 'OK',
            theme: 'dark'
        });
    };

    const handleFileChange = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setContextLoading(true);
        try {
            const result = await extractFromFile(file);
            setContextData(result);
            setShowContextInput(false);
        } catch (err) {
            showContextError(err);
        } finally {
            setContextLoading(false);
        }
    };

    const handleFetchUrl = async () => {
        if (!urlInput.trim()) return;
        setContextLoading(true);
        try {
            const result = await extractFromUrl(urlInput.trim());
            setContextData(result);
            setShowContextInput(false);
            setUrlInput('');
        } catch (err) {
            showContextError(err);
        } finally {
            setContextLoading(false);
        }
    };

    const toggleOption = (optionName) => {
        setSelectedOptions(prev =>
            prev.includes(optionName)
                ? prev.filter(name => name !== optionName)
                : [...prev, optionName]
        );
    };


    // const handleDropdownToggle = () => {
    //     // setIsDropdownOpen(prev => !prev);
    //     dispatch(setIsDropdownOpen(prev => !prev));
    // };

    // const handleCheckboxClick = (optionName) => {
    //     toggleOption(optionName); // Toggle the checkbox state
    //     // Prevent dropdown from closing
    // };


    // document.addEventListener('mousedown', handleClickOutside);
    // document.removeEventListener('mousedown', handleClickOutside);


    const hasCustomOption = otherChecked && customOption.trim().length > 0;

    const getDropdownText = () => {
        const total = selectedOptions.length + (hasCustomOption ? 1 : 0);
        if (total === 0) return "Select Functions";
        const first = selectedOptions[0] || customOption.trim();
        if (total === 1) return first;
        return (
            <>
                <span>{first}</span><span className='functionsCount'>+{total - 1}more</span>
            </>
        );
    };


    const onSubmit = async (e) => {
        e.preventDefault();
        // dispatch(setPromptId(null));
        // Set source to singlePrompt
        // Selecting a function is optional -- if none are picked (built-in or
        // custom), generation just goes off the user's own prompt text rather
        // than blocking submission or silently forcing a default framing.
        const finalOptions = hasCustomOption
            ? [...selectedOptions, customOption.trim()]
            : selectedOptions;

        const wordCount = prompt.trim().split(/\s+/).length; // Split by whitespace and count words
        if (wordCount < 3) {
            Swal.fire({
                title: 'Oops...!',
                text: 'Ensure your search query includes a minimum of three words.',
                icon: 'warning',
                confirmButtonText: 'OK',
                theme: 'dark'
            });
            return
        }
        try {
            handlePromptSearch(e, prompt, setPrompt, setLoading, setOpenAIResults, finalOptions, setSelectedOptions, dispatch, activeModel, contextData?.text || null, contextData ? { sourceType: contextData.sourceType, sourceName: contextData.sourceName } : null)
            setContextData(null);
            dispatch(setMainComponent('promptResult'));
            dispatch(setPromptSource('openAIPrompts'));
        } catch (error) {
            Swal.fire({
                title: 'Oops...!',
                text: 'Error while getting the OpenAIResults...',
                icon: 'error',
                confirmButtonText: 'OK',
                theme: 'dark'
            });
        }
    }



    return (
        <form onSubmit={onSubmit} className="composer">
            <textarea
                className="composerTextarea"
                value={`${prompt}`}
                placeholder="Describe your task..."
                onChange={(e) => setPrompt(e.target.value)}
                onClick={() => dispatch(setIsDropdownOpen(false))}
            />

            <div className="composerControls">
                <div className="composerControlsLeft">
                    <div className="dropdown selectFunctionsDiv" ref={dropdownRef}>
                        <button
                            className="selectFunctionsBtn d-flex align-items-center"
                            type="button"
                            aria-expanded={isDropdownOpen}
                            onClick={() => dispatch(setIsDropdownOpen(!isDropdownOpen))}
                        >
                            <span className='selectFunctionsTitle d-flex align-items-center'>{getDropdownText()}</span>
                            <img src={Arrow} width={16} height={16} alt='' className='selectFunctionsArrow' />
                        </button>
                        {isDropdownOpen && (
                            <ul className="dropdown-menu show">
                                {optionsList.map((option) => (
                                    <li key={option.name} onChange={() => toggleOption(option.name)}>
                                        <div className="dropdown-item">
                                            <div className="form-check" >
                                                <input
                                                    className="form-check-input"
                                                    type="checkbox"
                                                    id={`check-${option.name}`}
                                                    checked={selectedOptions.includes(option.name)}
                                                    role="button"
                                                />
                                                <label className="form-check-label" htmlFor={`check-${option.name}`} role="button">
                                                    {option.name}
                                                </label>
                                            </div>
                                        </div>
                                    </li>
                                ))}
                                <li>
                                    <div className="dropdown-item">
                                        <div className="form-check">
                                            <input
                                                className="form-check-input"
                                                type="checkbox"
                                                id="check-other"
                                                checked={otherChecked}
                                                onChange={() => setOtherChecked((prev) => !prev)}
                                                role="button"
                                            />
                                            <label className="form-check-label" htmlFor="check-other" role="button">
                                                Other
                                            </label>
                                        </div>
                                        {otherChecked && (
                                            <input
                                                type="text"
                                                className="form-control otherOptionInput mt-1"
                                                placeholder="Describe the expertise angle"
                                                value={customOption}
                                                onChange={(e) => setCustomOption(e.target.value)}
                                                onClick={(e) => e.stopPropagation()}
                                            />
                                        )}
                                    </div>
                                </li>
                            </ul>
                        )}
                    </div>

                    {models.length > 1 && (
                        <select
                            className="modelSelect"
                            aria-label="Model"
                            value={activeModel || ''}
                            onChange={(e) => setSelectedModel(e.target.value)}
                        >
                            {models.map((m) => (
                                <option key={m.id} value={m.id}>{m.label}</option>
                            ))}
                        </select>
                    )}

                    <div className="contextControl">
                        {contextData ? (
                            <div className="contextChip">
                                <span>
                                    {contextData.sourceType === 'url' ? '🔗' : '📄'} {contextData.sourceName} -- {contextData.characters} characters
                                    {contextData.truncated ? ' (truncated)' : ''}
                                    {contextData.cached ? ' (cached)' : ''}
                                </span>
                                <button type="button" className="btn-ghost" onClick={() => setShowContextPreview((v) => !v)}>
                                    {showContextPreview ? 'Hide' : 'Preview'}
                                </button>
                                {!prompt.includes('{content}') && (
                                    <button
                                        type="button"
                                        className="btn-ghost"
                                        title="Insert a {content} placeholder where you want this content to appear in your prompt"
                                        onClick={() => setPrompt((p) => (p.trim() ? `${p.trim()} {content}` : '{content}'))}
                                    >
                                        Insert {'{content}'}
                                    </button>
                                )}
                                <button type="button" className="btn-ghost" onClick={() => { setContextData(null); setShowContextPreview(false); }}>✕</button>
                                {contextData.warning && <div className="contextWarning">{contextData.warning}</div>}
                                {!prompt.includes('{content}') && (
                                    <div className="contextWarning">Without a {'{content}'} placeholder in your prompt, this is appended at the end.</div>
                                )}
                                {showContextPreview && <pre className="contextPreview">{contextData.text.slice(0, 800)}</pre>}
                            </div>
                        ) : showContextInput ? (
                            <div className="contextInputs">
                                <input
                                    type="file"
                                    accept=".txt,.md,.pdf,.docx"
                                    onChange={handleFileChange}
                                    disabled={contextLoading}
                                />
                                <input
                                    type="text"
                                    className="urlInput"
                                    placeholder="Or paste a URL"
                                    value={urlInput}
                                    onChange={(e) => setUrlInput(e.target.value)}
                                    disabled={contextLoading}
                                />
                                <button type="button" className="btn-secondary" onClick={handleFetchUrl} disabled={contextLoading || !urlInput.trim()}>
                                    {contextLoading ? 'Fetching...' : 'Fetch'}
                                </button>
                                <button type="button" className="btn-ghost" onClick={() => setShowContextInput(false)}>Cancel</button>
                            </div>
                        ) : (
                            <button type="button" className="btn-ghost addContextBtn" onClick={() => setShowContextInput(true)}>
                                + Context
                            </button>
                        )}
                    </div>
                </div>

                <button className="composerSubmit btn-primary d-flex align-items-center" type="submit" onClick={() => dispatch(setIsDropdownOpen(false))}>
                    <img src={AISubmit} width={18} height={18} alt='' />
                    <span>Generate</span>
                </button>
            </div>
        </form>
    );
};

export default HandlePrompt;