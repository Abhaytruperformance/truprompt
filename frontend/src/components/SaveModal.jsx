import React, { useState } from 'react';
import { Modal, Button } from 'react-bootstrap';
import { usePostPromptMutation, useUpdatePromptTagsMutation } from '../store/slices/truPromptSlice';
import { useGetDepartmentsQuery, useGetTagsQuery } from '../store/slices/orgSlice';
import Swal from 'sweetalert2';
import '@sweetalert2/theme-dark';
const SaveModal = ({ show, selectedPrompt, setShowSaveDialog, setOpenAIResults, id }) => {
    const [postPrompt] = usePostPromptMutation();
    const [updatePromptTags] = useUpdatePromptTagsMutation();
    const { data: departments = [] } = useGetDepartmentsQuery();
    const { data: tags = [] } = useGetTagsQuery();
    const [saveCategory, setSaveCategory] = useState("SEO");
    const [saveDepartment, setSaveDepartment] = useState("");
    const [saveTagIds, setSaveTagIds] = useState([]);
    const handleClose = () => {
        setShowSaveDialog(false);
    }
    // console.log(selectedPrompt);

    // Function to update savedStatus to true after successful DB push
    const updateSavedStatus = (setOpenAIResults, id, promptDBId) => {
        setOpenAIResults(prevResults => {
            const updatedResults = prevResults.map(result =>
                result.id === id ? { ...result, savedStatus: true, promptDBId: promptDBId } : result
            );

            // Store updated results in local storage
            const dataToStore = {
                results: updatedResults
            };
            localStorage.setItem('openAIResults', JSON.stringify(dataToStore));

            return updatedResults; // Return updated results for state
        });
    };

    const savePrompt = () => {
        const newPrompt = {
            category: saveCategory,
            userPrompt: selectedPrompt.userPrompt,
            prompt: selectedPrompt.prompt,
            optimizer: selectedPrompt.optimizer,
            departmentId: saveDepartment || null,
            sourceType: selectedPrompt.sourceType || null,
            sourceName: selectedPrompt.sourceName || null,
            sourceContext: selectedPrompt.sourceContext || null,
        };

        postPrompt(newPrompt)
            .unwrap()
            .then(async (response) => {
                updateSavedStatus(setOpenAIResults, selectedPrompt.id, response._id)
                if (saveTagIds.length > 0) {
                    try {
                        await updatePromptTags({ id: response._id, tagIds: saveTagIds }).unwrap();
                    } catch (tagErr) {
                        console.error('Error assigning tags:', tagErr);
                    }
                }
                // console.log('Prompt saved successfully:', response);
                Swal.fire({ // Show success alert
                    title: 'Success!',
                    text: 'Prompt saved successfully!',
                    icon: 'success',
                    confirmButtonText: 'OK',
                    theme: 'dark'
                }).then(() => {
                    handleClose(); // Close the modal after the user confirms the alert
                });
            })
            .catch((error) => {
                console.error('Error saving prompt:', error);
                Swal.fire({ // Show error alert
                    title: 'Error!',
                    text: 'Error saving prompt. Please try again.',
                    icon: 'error',
                    confirmButtonText: 'OK',
                    theme: 'dark'
                });
            });
    };

    const handleRadioChange = (e) => {
        setSaveCategory(e.target.value);
    };

    return (
        <Modal show={show} onHide={handleClose} className='customModal'>
            <Modal.Header closeButton>
                <Modal.Title>Save this prompt </Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <p>Do you want to save this prompt to the: {saveCategory}?</p>
                {["SEO", "Design", "Communication", "Web Development", "Lead Generation", "Lifecycle Marketing", "Business Development"].map((category) => (
                    <div key={category} className="form-check">
                        <input
                            className="form-check-input"
                            type="radio"
                            name="saveCategory"
                            id={category}
                            value={category}
                            checked={saveCategory === category}
                            onChange={handleRadioChange}
                        />
                        <label className="form-check-label" htmlFor={category}>
                            {category}
                        </label>
                    </div>
                ))}
                <div className="form-group mt-3">
                    <label htmlFor="saveDepartment">Department (optional)</label>
                    <select
                        id="saveDepartment"
                        className="form-select"
                        value={saveDepartment}
                        onChange={(e) => setSaveDepartment(e.target.value)}
                    >
                        <option value="">No department</option>
                        {departments.map((d) => (
                            <option key={d._id} value={d._id}>{d.name}</option>
                        ))}
                    </select>
                </div>
                <div className="form-group mt-3">
                    <label htmlFor="saveTags">Tags (optional, ctrl/cmd+click for multiple)</label>
                    <select
                        id="saveTags"
                        multiple
                        className="form-select"
                        value={saveTagIds}
                        onChange={(e) => setSaveTagIds(Array.from(e.target.selectedOptions).map((o) => o.value))}
                    >
                        {tags.map((t) => (
                            <option key={t._id} value={t._id}>{t.name}</option>
                        ))}
                    </select>
                </div>
            </Modal.Body>
            <Modal.Footer>
                <Button className='SaveBtn' variant="primary" onClick={savePrompt}>
                    Save
                </Button>
            </Modal.Footer>
        </Modal>
    );
}

export default SaveModal;