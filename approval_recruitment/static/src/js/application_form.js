console.log('Started Custom Job Form Script (With Watchdog)');

(function () {
    'use strict';

    // 1. Generate Random Number
    function generateRegNo() {
        var year = new Date().getFullYear();
        var rand = Math.floor(1000 + Math.random() * 9000);
        return 'LS/APP/' + year + '/' + rand;
    }

    var currentRegNo = null;

    function setRegistrationNumber() {
        var regField = document.getElementById('reg_no_field');
        if (!regField) return;

        // If we haven't generated one for this session yet, create it.
        if (!currentRegNo) {
            currentRegNo = generateRegNo();
        }

        // If the field is empty (or Odoo wiped it), put our number back!
        if (regField.value !== currentRegNo) {
            regField.value = currentRegNo;
            // console.log("Watchdog: Restored Registration Number -> " + currentRegNo);
        }
    }

    // 3. Main Initialization
    function initForm() {
        // --- 1. RECRUITMENT APPLICATION FORM LOGIC ---
        var recruitmentForm = document.getElementById('hr_recruitment_form');
        if (!recruitmentForm) { recruitmentForm = document.querySelector('form[action^="/website/form"]'); }

        // Only run this block if we are actually on the job application page
        if (recruitmentForm) {
            recruitmentForm.setAttribute('action', '/job/apply/save');
            recruitmentForm.setAttribute('method', 'POST');
            recruitmentForm.setAttribute('enctype', 'multipart/form-data');
            recruitmentForm.removeAttribute('data-model_name');
            recruitmentForm.removeAttribute('data-success-page');
            recruitmentForm.classList.remove('s_website_form');

            var oldBtn = recruitmentForm.querySelector('.s_website_form_send, button[type="submit"], .o_website_form_send');
            if (oldBtn) {
                var newBtn = oldBtn.cloneNode(true);
                oldBtn.parentNode.replaceChild(newBtn, oldBtn);
                newBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    setRegistrationNumber();
                    if (recruitmentForm.checkValidity()) { recruitmentForm.submit(); } else { recruitmentForm.reportValidity(); }
                });
            }

            setRegistrationNumber();
            var attempts = 0;
            var watchdog = setInterval(function() {
                setRegistrationNumber();
                attempts++;
                if (attempts > 15) { clearInterval(watchdog); }
            }, 200);
        }

        // =========================================================
        // ★ UPDATED: AESTHETIC TOGGLE LOGIC ★
        // =========================================================
        var typeSelector = document.getElementById('doc_type_selector');
        var dynamicContainer = document.getElementById('dynamic_sections');
        var expSection = document.getElementById('exp_docs');

        if (typeSelector && dynamicContainer && expSection) {
            console.log("Pre-Onboarding Aesthetic Logic Initialized");

            typeSelector.addEventListener('change', function () {
                var choice = this.value;
                console.log("Category Selected:", choice);

                // 1. Reveal the main form (Identity, Bank, Education)
                dynamicContainer.classList.remove('d-none');

                // 2. Reveal or hide the Experience-specific section
                if (choice === 'experienced') {
                    expSection.classList.remove('d-none');
                } else {
                    expSection.classList.add('d-none');
                }

                // 3. Smooth scroll to the start of the documents
                dynamicContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }


        // =========================================================
        // PHOTO PREVIEW LOGIC
        // =========================================================
        var photoInput  = document.getElementById('photo_upload');
        var previewBox  = document.getElementById('photo_preview_box');
        var placeholder = document.getElementById('photo_placeholder');
        var removeBtn   = document.getElementById('remove_photo');

        if (photoInput && previewBox) {
            photoInput.addEventListener('change', function () {
                var file = this.files[0];
                if (!file) return;
                if (file.size > 2 * 1024 * 1024) {
                    alert('File size must be less than 2MB!');
                    this.value = '';
                    return;
                }
                var reader = new FileReader();
                reader.onload = function (e) {
                    if (placeholder) placeholder.style.display = 'none';
                    var old = previewBox.querySelector('img');
                    if (old) old.remove();
                    var img = document.createElement('img');
                    img.src = e.target.result;
                    img.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:4px;';
                    previewBox.appendChild(img);
                    if (removeBtn) removeBtn.style.display = 'inline-block';
                };
                reader.readAsDataURL(file);
            });
        }

        if (removeBtn) {
            removeBtn.addEventListener('click', function () {
                if (photoInput) photoInput.value = '';
                var img = previewBox ? previewBox.querySelector('img') : null;
                if (img) img.remove();
                if (placeholder) placeholder.style.display = 'block';
                removeBtn.style.display = 'none';
            });
        }

        // =========================================================
        // TABLE ROW LOGIC
        // =========================================================
        function createEduRow() {
            var tr = document.createElement('tr');
            tr.className = 'edu_row';
            tr.innerHTML = '<td><input type="text" class="form-control form-control-sm border-0" name="edu_exam_name[]" placeholder="e.g., B.Tech"/></td>' +
                '<td><input type="text" class="form-control form-control-sm border-0" name="edu_passing_date[]" placeholder="MM/YYYY"/></td>' +
                '<td><input type="text" class="form-control form-control-sm border-0" name="edu_university[]"/></td>' +
                '<td><input type="number" step="0.01" class="form-control form-control-sm border-0" name="edu_marks_percentage[]"/></td>' +
                '<td><input type="text" class="form-control form-control-sm border-0" name="edu_main_subject[]"/></td>' +
                '<td class="text-center"><button type="button" class="btn btn-sm btn-outline-danger remove_edu_row"><i class="fa fa-trash"></i></button></td>';
            return tr;
        }

        function createExpRow() {
            var tr = document.createElement('tr');
            tr.className = 'exp_row';
            tr.innerHTML = '<td><textarea class="form-control form-control-sm border-0" name="exp_employer_name[]" rows="2"></textarea></td>' +
                '<td><input type="text" class="form-control form-control-sm border-0" name="exp_from_date[]" placeholder="DD/MM/YYYY"/></td>' +
                '<td><input type="text" class="form-control form-control-sm border-0" name="exp_to_date[]" placeholder="DD/MM/YYYY"/></td>' +
                '<td><input type="text" class="form-control form-control-sm border-0" name="exp_designation[]"/></td>' +
                '<td><textarea class="form-control form-control-sm border-0" name="exp_duties[]" rows="2"></textarea></td>' +
                '<td><input type="number" class="form-control form-control-sm border-0" name="exp_gross_salary[]"/></td>' +
                '<td><input type="text" class="form-control form-control-sm border-0" name="exp_pay_scale[]"/></td>' +
                '<td class="text-center"><button type="button" class="btn btn-sm btn-outline-danger remove_exp_row"><i class="fa fa-trash"></i></button></td>';
            return tr;
        }

        function attachListeners() {
            document.querySelectorAll('.remove_edu_row').forEach(function (btn) {
                btn.onclick = function () {
                    if (document.querySelectorAll('.edu_row').length > 1) { this.closest('tr').remove(); }
                    else { var inputs = this.closest('tr').querySelectorAll('input'); inputs.forEach(input => input.value = ''); }
                };
            });
            document.querySelectorAll('.remove_exp_row').forEach(function (btn) {
                btn.onclick = function () {
                    if (document.querySelectorAll('.exp_row').length > 1) { this.closest('tr').remove(); }
                    else { var inputs = this.closest('tr').querySelectorAll('input, textarea'); inputs.forEach(input => input.value = ''); }
                };
            });
        }

        var addEduBtn = document.getElementById('add_edu_row');
        if (addEduBtn) {
            addEduBtn.addEventListener('click', function () {
                var tbody = document.getElementById('edu_tbody');
                if (tbody) { tbody.appendChild(createEduRow()); attachListeners(); }
            });
        }

        var addExpBtn = document.getElementById('add_exp_row');
        if (addExpBtn) {
            addExpBtn.addEventListener('click', function () {
                var tbody = document.getElementById('exp_tbody');
                if (tbody) { tbody.appendChild(createExpRow()); attachListeners(); }
            });
        }

        var eduTbody = document.getElementById('edu_tbody');
        var expTbody = document.getElementById('exp_tbody');
        if (eduTbody && eduTbody.children.length === 0) { eduTbody.appendChild(createEduRow()); }
        if (expTbody && expTbody.children.length === 0) { expTbody.appendChild(createExpRow()); }
        attachListeners();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initForm);
    } else {
        initForm();
    }

})();