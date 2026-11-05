document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const statTotal = document.getElementById("statTotal");
    const statScheduled = document.getElementById("statScheduled");
    const statCompleted = document.getElementById("statCompleted");
    const statCancelled = document.getElementById("statCancelled");
    
    const tableBody = document.getElementById("appointmentsTableBody");
    const appointmentCountDisplay = document.getElementById("appointmentCountDisplay");
    const searchInput = document.getElementById("searchInput");
    const clearSearchBtn = document.getElementById("clearSearchBtn");
    const statusFilterSelect = document.getElementById("statusFilterSelect");
    const refreshBtn = document.getElementById("refreshBtn");
    
    const openNewModalBtn = document.getElementById("openNewModalBtn");
    const appointmentModal = document.getElementById("appointmentModal");
    const closeModalBtn = document.getElementById("closeModalBtn");
    const cancelModalBtn = document.getElementById("cancelModalBtn");
    const appointmentForm = document.getElementById("appointmentForm");
    const modalTitle = document.getElementById("modalTitle");
    const formAppointmentId = document.getElementById("formAppointmentId");
    const previewPetImg = document.getElementById("previewPetImg");
    const petTypeInput = document.getElementById("petTypeInput");
    
    const deleteConfirmModal = document.getElementById("deleteConfirmModal");
    const closeDeleteModalBtn = document.getElementById("closeDeleteModalBtn");
    const cancelDeleteBtn = document.getElementById("cancelDeleteBtn");
    const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");
    const deletePetName = document.getElementById("deletePetName");
    
    const currentTimeDisplay = document.getElementById("currentTimeDisplay");
    const toastContainer = document.getElementById("toastContainer");

    let appointmentToDelete = null;
    let searchDebounceTimer = null;

    // Helper: Select matching pet avatar based on species / breed
    function getPetImage(petType) {
        const type = (petType || '').toLowerCase();
        if (type.includes('dog') || type.includes('puppy') || type.includes('hound') || 
            type.includes('retriever') || type.includes('shepherd') || type.includes('poodle') || 
            type.includes('beagle') || type.includes('labrador') || type.includes('terrier')) {
            return '/static/images/pets/dog.svg';
        }
        if (type.includes('cat') || type.includes('kitten') || type.includes('feline') || 
            type.includes('siamese') || type.includes('shorthair') || type.includes('persian')) {
            return '/static/images/pets/cat.svg';
        }
        if (type.includes('rabbit') || type.includes('bunny') || type.includes('hare') || type.includes('lop')) {
            return '/static/images/pets/rabbit.svg';
        }
        if (type.includes('bird') || type.includes('parrot') || type.includes('canary') || type.includes('finch')) {
            return '/static/images/pets/bird.svg';
        }
        return '/static/images/pets/other.svg';
    }

    // Live avatar preview in modal when typing breed/species
    if (petTypeInput && previewPetImg) {
        petTypeInput.addEventListener("input", (e) => {
            previewPetImg.src = getPetImage(e.target.value);
        });
    }

    // Initialize clock
    function updateClock() {
        const now = new Date();
        const options = { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
        currentTimeDisplay.textContent = now.toLocaleDateString(undefined, options);
    }
    updateClock();
    setInterval(updateClock, 30000);

    // Toast Notifications
    function showToast(message, type = "success") {
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        
        let iconSvg = '';
        if (type === 'success') {
            iconSvg = `<svg viewBox="0 0 20 20" width="18" height="18" fill="#059669">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>`;
        } else {
            iconSvg = `<svg viewBox="0 0 20 20" width="18" height="18" fill="#dc2626">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
            </svg>`;
        }

        toast.innerHTML = `${iconSvg}<span>${escapeHtml(message)}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // Helper: Escape HTML
    function escapeHtml(text) {
        if (!text) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Helper: Format Date
    function formatDate(dateStr) {
        if (!dateStr) return "-";
        try {
            const parts = dateStr.split('-');
            if (parts.length === 3) {
                const date = new Date(parts[0], parts[1] - 1, parts[2]);
                return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
            }
            return dateStr;
        } catch {
            return dateStr;
        }
    }

    // Helper: Format Time
    function formatTime(timeStr) {
        if (!timeStr) return "-";
        try {
            const parts = timeStr.split(':');
            if (parts.length >= 2) {
                let hours = parseInt(parts[0], 10);
                const minutes = parts[1];
                const ampm = hours >= 12 ? 'PM' : 'AM';
                hours = hours % 12;
                hours = hours ? hours : 12;
                return `${hours}:${minutes} ${ampm}`;
            }
            return timeStr;
        } catch {
            return timeStr;
        }
    }

    // Fetch Stats
    async function loadStats() {
        try {
            const response = await fetch('/api/stats');
            if (!response.ok) throw new Error("Could not load stats");
            const data = await response.json();
            
            statTotal.textContent = data.total ?? 0;
            statScheduled.textContent = data.scheduled ?? 0;
            statCompleted.textContent = data.completed ?? 0;
            statCancelled.textContent = data.cancelled ?? 0;
        } catch (err) {
            console.error("Error loading stats:", err);
        }
    }

    // Fetch Appointments
    async function loadAppointments() {
        const query = searchInput.value.trim();
        const status = statusFilterSelect.value;
        
        let url = `/api/appointments?q=${encodeURIComponent(query)}&status=${encodeURIComponent(status)}`;

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error("Could not load appointments");
            const appointments = await response.json();
            
            renderAppointments(appointments);
            appointmentCountDisplay.textContent = `Showing ${appointments.length} patient appointment${appointments.length === 1 ? '' : 's'}`;
        } catch (err) {
            console.error("Error loading appointments:", err);
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">
                        <p style="color: var(--danger)">Failed to load appointments. Please check connection.</p>
                    </td>
                </tr>
            `;
            showToast("Failed to fetch appointments", "error");
        }
    }

    // Render Table Rows with Pet Avatars
    function renderAppointments(appointments) {
        if (!appointments || appointments.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">
                        <img src="/static/images/empty-illustration.svg" alt="No appointments" class="empty-img">
                        <p style="font-weight: 600; color: var(--text-secondary);">No appointments found matching your criteria.</p>
                        <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem;">Try adjusting your search query or clear filters.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML = appointments.map(apt => {
            const petImgSrc = getPetImage(apt.pet_type);
            return `
            <tr data-id="${apt.id}">
                <td>
                    <div class="pet-cell">
                        <div class="pet-avatar-wrap">
                            <img src="${petImgSrc}" alt="${escapeHtml(apt.pet_type)}" class="pet-avatar-img">
                        </div>
                        <div class="pet-meta">
                            <span class="pet-name">${escapeHtml(apt.pet_name)}</span>
                            <span class="pet-type">${escapeHtml(apt.pet_type)}</span>
                        </div>
                    </div>
                </td>
                <td>
                    <div class="owner-cell">
                        <span class="owner-name">${escapeHtml(apt.owner_name)}</span>
                        <div class="owner-contact">
                            <span>📞 ${escapeHtml(apt.owner_phone)}</span>
                            ${apt.owner_email ? ` · <span>✉️ ${escapeHtml(apt.owner_email)}</span>` : ''}
                        </div>
                    </div>
                </td>
                <td>
                    <div>
                        <span class="date-primary">${formatDate(apt.appointment_date)}</span>
                        <div class="time-sub">⏰ ${formatTime(apt.appointment_time)}</div>
                    </div>
                </td>
                <td>
                    <div>
                        <span class="service-title">${escapeHtml(apt.service)}</span>
                        ${apt.notes ? `<div class="service-notes" title="${escapeHtml(apt.notes)}">${escapeHtml(apt.notes)}</div>` : ''}
                    </div>
                </td>
                <td>
                    <select class="status-select-inline ${apt.status}" data-id="${apt.id}">
                        <option value="Scheduled" ${apt.status === 'Scheduled' ? 'selected' : ''}>Scheduled</option>
                        <option value="Completed" ${apt.status === 'Completed' ? 'selected' : ''}>Completed</option>
                        <option value="Cancelled" ${apt.status === 'Cancelled' ? 'selected' : ''}>Cancelled</option>
                    </select>
                </td>
                <td class="text-right">
                    <div class="action-buttons">
                        <button class="btn-table-neu edit-btn" title="Edit Appointment" data-id="${apt.id}">
                            <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor">
                                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
                            </svg>
                        </button>
                        <button class="btn-table-neu delete-action delete-btn" title="Delete Appointment" data-id="${apt.id}" data-name="${escapeHtml(apt.pet_name)}">
                            <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor">
                                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
            `;
        }).join('');

        // Attach event listeners for inline status change
        document.querySelectorAll('.status-select-inline').forEach(select => {
            select.addEventListener('change', async (e) => {
                const id = e.target.getAttribute('data-id');
                const newStatus = e.target.value;
                await updateStatus(id, newStatus, e.target);
            });
        });

        // Attach event listeners for Edit
        document.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-id');
                openEditModal(id);
            });
        });

        // Attach event listeners for Delete
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-id');
                const name = btn.getAttribute('data-name');
                openDeleteModal(id, name);
            });
        });
    }

    // Quick Status Update
    async function updateStatus(id, newStatus, selectElement) {
        try {
            const response = await fetch(`/api/appointments/${id}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || "Failed to update status");
            }

            selectElement.className = `status-select-inline ${newStatus}`;
            showToast(`Status updated to ${newStatus}`);
            loadStats();
        } catch (err) {
            console.error("Error updating status:", err);
            showToast(err.message, "error");
            loadAppointments();
        }
    }

    // Open New Appointment Modal
    function openNewModal() {
        formAppointmentId.value = "";
        modalTitle.textContent = "New Appointment";
        appointmentForm.reset();
        
        // Default avatar
        previewPetImg.src = "/static/images/pets/dog.svg";

        // Default date to today, status to Scheduled
        const today = new Date().toISOString().split('T')[0];
        document.getElementById("dateInput").value = today;
        document.getElementById("statusInput").value = "Scheduled";
        
        appointmentModal.classList.add("active");
        document.getElementById("petNameInput").focus();
    }

    // Open Edit Appointment Modal
    async function openEditModal(id) {
        try {
            const response = await fetch(`/api/appointments/${id}`);
            if (!response.ok) throw new Error("Failed to load appointment details");
            const apt = await response.json();

            formAppointmentId.value = apt.id;
            modalTitle.textContent = `Edit Appointment: ${apt.pet_name}`;
            
            previewPetImg.src = getPetImage(apt.pet_type);

            document.getElementById("petNameInput").value = apt.pet_name || "";
            document.getElementById("petTypeInput").value = apt.pet_type || "";
            document.getElementById("ownerNameInput").value = apt.owner_name || "";
            document.getElementById("ownerPhoneInput").value = apt.owner_phone || "";
            document.getElementById("ownerEmailInput").value = apt.owner_email || "";
            document.getElementById("dateInput").value = apt.appointment_date || "";
            document.getElementById("timeInput").value = apt.appointment_time || "";
            document.getElementById("serviceInput").value = apt.service || "";
            document.getElementById("statusInput").value = apt.status || "Scheduled";
            document.getElementById("notesInput").value = apt.notes || "";

            appointmentModal.classList.add("active");
            document.getElementById("petNameInput").focus();
        } catch (err) {
            console.error("Error opening edit modal:", err);
            showToast("Could not retrieve appointment details", "error");
        }
    }

    function closeModal() {
        appointmentModal.classList.remove("active");
        appointmentForm.reset();
    }

    // Submit New or Updated Appointment
    appointmentForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const id = formAppointmentId.value;
        const payload = {
            pet_name: document.getElementById("petNameInput").value.trim(),
            pet_type: document.getElementById("petTypeInput").value.trim(),
            owner_name: document.getElementById("ownerNameInput").value.trim(),
            owner_phone: document.getElementById("ownerPhoneInput").value.trim(),
            owner_email: document.getElementById("ownerEmailInput").value.trim(),
            appointment_date: document.getElementById("dateInput").value.trim(),
            appointment_time: document.getElementById("timeInput").value.trim(),
            service: document.getElementById("serviceInput").value.trim(),
            status: document.getElementById("statusInput").value.trim(),
            notes: document.getElementById("notesInput").value.trim()
        };

        const isEdit = Boolean(id);
        const url = isEdit ? `/api/appointments/${id}` : '/api/appointments';
        const method = isEdit ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || "Failed to save appointment");
            }

            closeModal();
            showToast(isEdit ? "Appointment updated successfully!" : "Appointment scheduled successfully!");
            await Promise.all([loadStats(), loadAppointments()]);
        } catch (err) {
            console.error("Save error:", err);
            showToast(err.message, "error");
        }
    });

    // Delete Modal Actions
    function openDeleteModal(id, petName) {
        appointmentToDelete = id;
        deletePetName.textContent = petName;
        deleteConfirmModal.classList.add("active");
    }

    function closeDeleteModal() {
        appointmentToDelete = null;
        deleteConfirmModal.classList.remove("active");
    }

    confirmDeleteBtn.addEventListener("click", async () => {
        if (!appointmentToDelete) return;
        try {
            const response = await fetch(`/api/appointments/${appointmentToDelete}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || "Failed to delete appointment");
            }

            closeDeleteModal();
            showToast("Appointment deleted successfully");
            await Promise.all([loadStats(), loadAppointments()]);
        } catch (err) {
            console.error("Delete error:", err);
            showToast(err.message, "error");
        }
    });

    // Search and Filter Events
    searchInput.addEventListener("input", () => {
        clearSearchBtn.style.display = searchInput.value ? "block" : "none";
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => {
            loadAppointments();
        }, 250);
    });

    clearSearchBtn.addEventListener("click", () => {
        searchInput.value = "";
        clearSearchBtn.style.display = "none";
        loadAppointments();
    });

    statusFilterSelect.addEventListener("change", () => {
        loadAppointments();
    });

    refreshBtn.addEventListener("click", () => {
        loadStats();
        loadAppointments();
        showToast("Dashboard refreshed");
    });

    // Modal triggers
    openNewModalBtn.addEventListener("click", openNewModal);
    closeModalBtn.addEventListener("click", closeModal);
    cancelModalBtn.addEventListener("click", closeModal);
    
    closeDeleteModalBtn.addEventListener("click", closeDeleteModal);
    cancelDeleteBtn.addEventListener("click", closeDeleteModal);

    // Close modals on clicking outside or ESC
    window.addEventListener("click", (e) => {
        if (e.target === appointmentModal) closeModal();
        if (e.target === deleteConfirmModal) closeDeleteModal();
    });

    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeModal();
            closeDeleteModal();
        }
    });

    // Initial Load
    loadStats();
    loadAppointments();
});
