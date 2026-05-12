console.log('Custom Job Form JS Loaded');

(function () {
    'use strict';

    // ─────────────────────────────────────────────────────────
    // REGISTRATION NUMBER
    // ─────────────────────────────────────────────────────────
    function generateRegNo() {
        var year = new Date().getFullYear();
        var rand = Math.floor(1000 + Math.random() * 9000);
        return 'LS/APP/' + year + '/' + rand;
    }

    var currentRegNo = null;

    function setRegistrationNumber() {
        var f = document.getElementById('reg_no_field');
        if (!f) return false;
        if (!currentRegNo) { currentRegNo = generateRegNo(); }
        f.value = currentRegNo;
        return true;
    }

    // ── WATCHDOG 1: Fast watchdog ──
    var wdCount = 0;
    var wd = setInterval(function () {
        setRegistrationNumber();
        if (++wdCount > 50) { clearInterval(wd); }
    }, 100);

    // ── WATCHDOG 2: Slow persistent watchdog ──
    setInterval(function () {
        var f = document.getElementById('reg_no_field');
        if (f && currentRegNo && f.value !== currentRegNo) {
            f.value = currentRegNo;
            console.log('RegNo restored by persistent watchdog');
        }
    }, 500);

    // ─────────────────────────────────────────────────────────
    // FIELD VALIDATORS
    // ─────────────────────────────────────────────────────────
    function setError(el, msg) {
        el.classList.add('is-invalid');
        el.classList.remove('is-valid');
        var fb = el.nextElementSibling;
        if (fb && fb.classList.contains('invalid-feedback')) { fb.textContent = msg; }
    }

    function clearError(el) {
        el.classList.remove('is-invalid');
        el.classList.add('is-valid');
    }

    function validateDOB(el) {
        if (!el.value) { setError(el, 'Date of birth is required.'); return false; }
        var yr = new Date(el.value).getFullYear();
        if (yr < 1900 || yr > 2099) { setError(el, 'Enter a valid year (1900-2099).'); return false; }
        clearError(el); return true;
    }

    function initNumericField(id, maxLen, exactLen, label) {
        var el = document.getElementById(id);
        if (!el) return;

        function cleanInput() {
            el.value = el.value.replace(/[^0-9]/g, '').slice(0, maxLen);
        }

        el.addEventListener('keypress', function (e) {
            if (e.ctrlKey || e.metaKey) return;
            if (e.key.length === 1 && !/[0-9]/.test(e.key)) { e.preventDefault(); }
        });

        el.addEventListener('input', cleanInput);
        el.addEventListener('change', cleanInput);

        el.addEventListener('blur', function () {
            cleanInput();
            if (exactLen && this.value.length !== exactLen) {
                setError(this, label + ' must be exactly ' + exactLen + ' digits.');
            } else if (!this.value.length) {
                setError(this, label + ' is required.');
            } else {
                clearError(this);
            }
        });
    }

    function attachCgpa(input) {
        input.addEventListener('keydown', function (e) {
            if (['e', 'E', '+', '-'].indexOf(e.key) !== -1) { e.preventDefault(); }
        });
        input.addEventListener('input', function () {
            var v = this.value.replace(/[^0-9.]/g, '');
            var p = v.split('.');
            if (p.length > 2) { v = p[0] + '.' + p.slice(1).join(''); }
            this.value = v;
        });
    }

    // ─────────────────────────────────────────────────────────
    // TABLE ROWS
    // ─────────────────────────────────────────────────────────
    function createEduRow() {
        var tr = document.createElement('tr');
        tr.className = 'edu_row';
        tr.innerHTML =
            '<td><input type="text" class="form-control form-control-sm border-0 edu-req" name="edu_exam_name[]" placeholder="e.g., B.Tech"/></td>' +
            '<td><input type="date" class="form-control form-control-sm border-0" name="edu_passing_date[]" min="1950-01-01" max="2099-12-31"/></td>' +
            '<td><input type="text" class="form-control form-control-sm border-0 edu-req" name="edu_university[]" placeholder="Institution"/></td>' +
            '<td><input type="number" step="0.01" min="0" max="100" class="form-control form-control-sm border-0 cgpa-inp" name="edu_marks_percentage[]" placeholder="85"/></td>' +
            '<td><input type="text" class="form-control form-control-sm border-0" name="edu_main_subject[]" placeholder="e.g., CSE"/></td>' +
            '<td class="text-center"><button type="button" class="btn btn-sm btn-outline-danger remove_edu_row"><i class="fa fa-trash"></i></button></td>';
        var cgpa = tr.querySelector('.cgpa-inp');
        if (cgpa) { attachCgpa(cgpa); }
        return tr;
    }

    function createExpRow() {
        var tr = document.createElement('tr');
        tr.className = 'exp_row';
        tr.innerHTML =
            '<td><input type="text" class="form-control form-control-sm border-0 exp-req" name="exp_employer_name[]" placeholder="Employer"/></td>' +
            '<td><input type="date" class="form-control form-control-sm border-0" name="exp_from_date[]" min="1950-01-01" max="2099-12-31"/></td>' +
            '<td><input type="date" class="form-control form-control-sm border-0" name="exp_to_date[]" min="1950-01-01" max="2099-12-31"/></td>' +
            '<td><input type="text" class="form-control form-control-sm border-0 exp-req" name="exp_designation[]" placeholder="Designation"/></td>' +
            '<td><input type="text" class="form-control form-control-sm border-0" name="exp_duties[]" placeholder="Nature of duties"/></td>' +
            '<td><input type="number" step="0.01" min="0" class="form-control form-control-sm border-0 cgpa-inp" name="exp_gross_salary[]" placeholder="0.00"/></td>' +
            '<td><input type="text" class="form-control form-control-sm border-0" name="exp_pay_scale[]" placeholder="e.g., 30k-50k"/></td>' +
            '<td class="text-center"><button type="button" class="btn btn-sm btn-outline-danger remove_exp_row"><i class="fa fa-trash"></i></button></td>';
        var sal = tr.querySelector('.cgpa-inp');
        if (sal) { attachCgpa(sal); }
        return tr;
    }

    function isLastRowValid(tbody, reqClass) {
        var rows = tbody.querySelectorAll('tr');
        if (!rows.length) return true;
        var last = rows[rows.length - 1];
        var ok = true;
        last.querySelectorAll('.' + reqClass).forEach(function (f) {
            if (!f.value.trim()) { f.classList.add('is-invalid'); ok = false; }
            else { f.classList.remove('is-invalid'); }
        });
        return ok;
    }

    function attachRowListeners() {
        document.querySelectorAll('.remove_edu_row, .remove_exp_row').forEach(function (btn) {
            btn.onclick = function () { this.closest('tr').remove(); };
        });
    }

    function showTableError(spanId) {
        var el = document.getElementById(spanId);
        if (!el) return;
        el.style.display = 'inline';
        setTimeout(function () { el.style.display = 'none'; }, 3000);
    }

    // ─────────────────────────────────────────────────────────
    // PHOTO & UPLOADS
    // ─────────────────────────────────────────────────────────
    function initPhotoPreview() {
        var inp = document.getElementById('photo_upload');
        var box = document.getElementById('photo_preview_box');
        if (!inp || !box) return;
        inp.addEventListener('change', function () {
            var file = this.files[0];
            if (!file) return;
            var r = new FileReader();
            r.onload = function (e) {
                box.innerHTML = '<img src="' + e.target.result + '" style="width:100%;height:100%;object-fit:cover;border-radius:4px;">';
            };
            r.readAsDataURL(file);
        });
    }

    function initAdvancedUploads() {
        var lb    = document.getElementById('obLightbox');
        var lbImg = document.getElementById('obLightboxImg');
        var lbPdf = document.getElementById('obLightboxPdf');

        document.querySelectorAll('.file-input-advanced').forEach(function (input) {
            input.addEventListener('change', function () {
                var container = this.closest('.ob-upload-zone').querySelector('.ob-file-list');
                if (!this.hasAttribute('multiple')) { container.innerHTML = ''; }
                Array.from(this.files).forEach(function (file) {
                    var id = 'file_' + Math.random().toString(36).substr(2, 9);
                    var r  = new FileReader();
                    r.onload = function (e) {
                        var isPdf = file.type === 'application/pdf';
                        var src   = e.target.result;
                        container.insertAdjacentHTML('beforeend',
                            '<div id="' + id + '" style="display:flex;align-items:center;gap:10px;margin-top:8px;padding:10px;border:1px solid #ede9ff;border-radius:12px;background:#fff;">' +
                            '<div style="width:40px;height:40px;flex-shrink:0;">' +
                            (isPdf ? '<i class="fa fa-file-pdf-o fa-2x" style="color:#e24b4a"></i>'
                                   : '<img src="' + src + '" style="width:100%;height:100%;object-fit:cover;border-radius:6px;">') +
                            '</div><div style="flex:1;min-width:0;font-size:.8rem;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + file.name + '</div>' +
                            '<button type="button" class="btn btn-sm btn-light preview-btn" data-src="' + src + '" data-type="' + (isPdf ? 'pdf' : 'img') + '"><i class="fa fa-eye"></i></button>' +
                            '<button type="button" class="btn btn-sm btn-outline-danger" onclick="document.getElementById(\'' + id + '\').remove()"><i class="fa fa-trash"></i></button>' +
                            '</div>');
                    };
                    r.readAsDataURL(file);
                });
            });
        });

        document.addEventListener('click', function (e) {
            var btn = e.target.closest('.preview-btn');
            if (btn && lb) {
                var src  = btn.getAttribute('data-src');
                var type = btn.getAttribute('data-type');
                if (type === 'pdf') { lbImg.style.display = 'none'; lbPdf.style.display = 'block'; lbPdf.src = src; }
                else                { lbPdf.style.display = 'none'; lbImg.style.display = 'block'; lbImg.src = src; }
                lb.classList.add('is-open');
            }
        });

        var lbClose = document.getElementById('obLightboxClose');
        if (lbClose) { lbClose.onclick = function () { lb.classList.remove('is-open'); lbPdf.src = ''; }; }
    }

    function initCategoryToggle() {
        var sel  = document.getElementById('doc_type_selector');
        var wrap = document.getElementById('dynamic_sections');
        var exp  = document.getElementById('exp_docs');
        if (!sel || !wrap || !exp) return;
        sel.addEventListener('change', function () {
            wrap.classList.remove('d-none');
            this.value === 'experienced' ? exp.classList.remove('d-none') : exp.classList.add('d-none');
            wrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    // ─────────────────────────────────────────────────────────
    // SUBMIT VIA FETCH - FIXED TO CATCH ERRORS
    // ─────────────────────────────────────────────────────────
    function submitFormViaFetch(form) {
        setRegistrationNumber();

        var btn = form.querySelector('.s_website_form_send, a[role="button"], button[type="submit"]');
        if (btn) {
            btn.style.opacity = '0.6';
            btn.style.pointerEvents = 'none';
            btn.textContent = 'Submitting...';
        }

        var formData = new FormData(form);

        fetch('/job/apply/save', {
            method: 'POST',
            body: formData,
        })
        .then(function(response) {
            // Get the raw HTML/text back from our Python controller
            return response.text();
        })
        .then(function(text) {
            // If the python controller threw our red error box, show it!
            if (text.includes("Odoo Save Failed!")) {
                document.open();
                document.write(text);
                document.close();
            } else {
                // If there's no error, safely redirect
                window.location.href = '/contactus-thank-you';
            }
        })
        .catch(function (err) {
            console.error('Submit error:', err);
            btn.textContent = 'Submit Failed';
        });
    }

    // ─────────────────────────────────────────────────────────
    // MAIN INIT
    // ─────────────────────────────────────────────────────────
    function initForm() {
        setRegistrationNumber();

        var form = document.getElementById('hr_recruitment_form')
            || document.querySelector('form[action*="/website/form"]')
            || document.querySelector('form[action*="apply"]')
            || document.querySelector('.s_website_form form')
            || document.querySelector('form');

        if (!form) {
            console.warn('Job application form not found');
        } else {
            form.removeAttribute('data-model_name');
            form.removeAttribute('data-success-page');
            form.removeAttribute('data-success_page');
            form.removeAttribute('data-force_action');
            form.classList.remove('s_website_form');

            var submitEl = form.querySelector('.s_website_form_send')
                || form.querySelector('a[role="button"]')
                || form.querySelector('button[type="submit"]');

            if (submitEl) {
                var newSubmit = submitEl.cloneNode(true);
                submitEl.parentNode.replaceChild(newSubmit, submitEl);

                newSubmit.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();

                    var dob = document.getElementById('date_of_birth');
                    if (dob && !validateDOB(dob)) { dob.focus(); return; }

                    if (!form.checkValidity()) { form.reportValidity(); return; }

                    submitFormViaFetch(form);
                });
            }
        }

        var dob = document.getElementById('date_of_birth');
        if (dob) { dob.addEventListener('change', function () { validateDOB(this); }); }

        initNumericField('partner_phone', 10, 10, 'Mobile number');
        initNumericField('pincode', 6, 6, 'PIN code');

        initPhotoPreview();
        initAdvancedUploads();
        initCategoryToggle();

        var addEdu = document.getElementById('add_edu_row');
        if (addEdu) {
            addEdu.addEventListener('click', function () {
                var tbody = document.getElementById('edu_tbody');
                if (!tbody) return;
                if (!isLastRowValid(tbody, 'edu-req')) { showTableError('edu_error'); return; }
                tbody.appendChild(createEduRow());
                attachRowListeners();
            });
        }

        var addExp = document.getElementById('add_exp_row');
        if (addExp) {
            addExp.addEventListener('click', function () {
                var tbody = document.getElementById('exp_tbody');
                if (!tbody) return;
                if (!isLastRowValid(tbody, 'exp-req')) { showTableError('exp_error'); return; }
                tbody.appendChild(createExpRow());
                attachRowListeners();
            });
        }

        attachRowListeners();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initForm);
    } else {
        initForm();
    }

})();