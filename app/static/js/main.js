/* CampusConnect Interactivity & AJAX Utilities */

document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss alert notifications after 5 seconds
    const alerts = document.querySelectorAll('.flash-alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // Image preview helper for file inputs
    const imageInputs = document.querySelectorAll('input[type="file"][data-preview]');
    imageInputs.forEach(input => {
        const previewId = input.getAttribute('data-preview');
        const previewElem = document.getElementById(previewId);
        if (previewElem) {
            input.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file && file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = (evt) => {
                        previewElem.src = evt.target.result;
                        previewElem.classList.remove('hidden');
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    });

    // Modal Helpers
    window.openModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        }
    };

    window.closeModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
    };

    // Attendance Toggle Handler (AJAX)
    const attendanceToggles = document.querySelectorAll('.attendance-toggle');
    attendanceToggles.forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            const regId = this.getAttribute('data-reg-id');
            const eventId = this.getAttribute('data-event-id');
            const currentAttended = this.getAttribute('data-attended') === 'true';
            const newAttended = !currentAttended;

            const formData = new FormData();
            formData.append('registration_id', regId);
            formData.append('attended', newAttended);

            try {
                const response = await fetch(`/coordinator/events/${eventId}/attendance`, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const data = await response.json();
                if (data.success) {
                    this.setAttribute('data-attended', data.attended);
                    if (data.attended) {
                        this.className = 'attendance-toggle px-3.5 py-1.5 rounded-full text-xs font-semibold badge-emerald inline-flex items-center gap-1.5 cursor-pointer transition-all';
                        this.innerHTML = '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg> Attended';
                    } else {
                        this.className = 'attendance-toggle px-3.5 py-1.5 rounded-full text-xs font-semibold badge-amber inline-flex items-center gap-1.5 cursor-pointer transition-all';
                        this.innerHTML = '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg> Absent';
                    }
                }
            } catch (err) {
                console.error('Error updating attendance:', err);
            }
        });
    });
});
