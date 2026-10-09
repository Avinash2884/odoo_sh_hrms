console.log('Pre-Offer / Pre-Onboarding JS Loaded');

(function () {
    'use strict';

    // ─────────────────────────────────────────────────────────
    // 1. DYNAMIC DROPDOWN LOGIC (Universal Fix for Both Forms)
    // ─────────────────────────────────────────────────────────
    function initDynamicDropdowns() {
        var categorySelect = document.getElementById('doc_type_selector');
        var dynamicSections = document.getElementById('dynamic_sections');
        var expDocs = document.getElementById('exp_docs');
        var incomeSelect = document.getElementById('income_type_select');

        // --- C. Handle Income Proof (Specific to Pre-Offer) ---
        function handleIncomeChange() {
            var payslipWrap = document.getElementById('payslip_wrapper');
            var bankWrap = document.getElementById('bank_wrapper');
            var payslipInput = document.getElementById('payslip_input') || document.querySelector('input[name="payslips"]');
            var bankInput = document.getElementById('bank_input') || document.querySelector('input[name="income_bank_statement"]');

            var payslipUploaded = payslipWrap ? payslipWrap.querySelector('.text-success') !== null : false;
            var bankUploaded = bankWrap ? bankWrap.querySelector('.text-success') !== null : false;

            if(payslipWrap) payslipWrap.classList.add('d-none');
            if(bankWrap) bankWrap.classList.add('d-none');
            if(payslipInput) payslipInput.required = false;
            if(bankInput) bankInput.required = false;

            if (categorySelect && categorySelect.value === 'experienced' && incomeSelect) {
                if (incomeSelect.value === 'payslip') {
                    if(payslipWrap) payslipWrap.classList.remove('d-none');
                    if(payslipInput && !payslipUploaded) payslipInput.required = true;
                } else if (incomeSelect.value === 'bank') {
                    if(bankWrap) bankWrap.classList.remove('d-none');
                    if(bankInput && !bankUploaded) bankInput.required = true;
                }
            }
        }

        if (incomeSelect) {
            incomeSelect.addEventListener('change', handleIncomeChange);
        }

        // --- A. Handle Category (Fresher vs Exp) for BOTH pages ---
        if (categorySelect && dynamicSections && expDocs) {
            function handleCategoryChange() {
                // Fallback for Pre-Onboarding (No incomeSelect, payslips are direct)
                var payslipInput = document.querySelector('input[name="payslips"]');
                var payslipUploaded = payslipInput ? payslipInput.closest('.ob-upload-zone').querySelector('.text-success') !== null : false;

                // FIX: Only reveal sections if an actual track is chosen
                if (categorySelect.value === 'experienced' || categorySelect.value === 'fresher') {
                    dynamicSections.classList.remove('d-none');

                    if (categorySelect.value === 'experienced') {
                        expDocs.classList.remove('d-none');

                        if (incomeSelect) {
                            handleIncomeChange(); // Pre-Offer track
                        } else if (payslipInput && !payslipUploaded) {
                            payslipInput.required = true; // Pre-Onboarding track
                        }
                    } else {
                        // FRESHER TRACK SELECTED
                        expDocs.classList.add('d-none');

                        // Cleanly wipe required states off hidden inputs
                        var expInputs = expDocs.querySelectorAll('input, select, textarea');
                        expInputs.forEach(function(inp) {
                            inp.required = false;
                        });
                    }
                } else {
                    // FORCE HIDE EVERYTHING if on "-- SELECT CATEGORY --"
                    dynamicSections.classList.add('d-none');
                    expDocs.classList.add('d-none');
                }
            }

            categorySelect.addEventListener('change', handleCategoryChange);
            handleCategoryChange();
            setTimeout(handleCategoryChange, 150);
        }

        // --- B. Education Level (UG vs PG) (Pre-Offer Only) ---
        var eduSelect = document.getElementById('edu_level_select');
        if (eduSelect) {
            function handleEduChange() {
                var detailWrap = document.getElementById('edu_detail_wrapper');
                var ugWrap = document.getElementById('ug_file_wrapper');
                var pgWrap = document.getElementById('pg_file_wrapper');
                var detailInput = document.getElementById('edu_detail_input');
                var ugInput = document.getElementById('ug_file_input');
                var pgInput = document.getElementById('pg_file_input');

                var ugUploaded = ugWrap ? ugWrap.querySelector('.text-success') !== null : false;
                var pgUploaded = pgWrap ? pgWrap.querySelector('.text-success') !== null : false;

                if(detailWrap) detailWrap.classList.add('d-none');
                if(ugWrap) ugWrap.classList.add('d-none');
                if(pgWrap) pgWrap.classList.add('d-none');
                if(detailInput) detailInput.required = false;
                if(ugInput) ugInput.required = false;
                if(pgInput) pgInput.required = false;

                if (eduSelect.value) {
                    if(detailWrap) detailWrap.classList.remove('d-none');
                    if(detailInput && !detailInput.hasAttribute('readonly')) detailInput.required = true;

                    if (eduSelect.value === 'ug') {
                        if(ugWrap) ugWrap.classList.remove('d-none');
                        if(ugInput && !ugUploaded) ugInput.required = true;

                    } else if (eduSelect.value === 'pg') {
                        if(ugWrap) ugWrap.classList.remove('d-none');
                        if(ugInput && !ugUploaded) ugInput.required = true;

                        if(pgWrap) pgWrap.classList.remove('d-none');
                        if(pgInput && !pgUploaded) pgInput.required = true;
                    }
                }
            }
            eduSelect.addEventListener('change', handleEduChange);
            handleEduChange();
            setTimeout(handleEduChange, 150);
        }
    }

    // ─────────────────────────────────────────────────────────
    // 2. ADVANCED UPLOADS (Lightbox & Previews)
    // ─────────────────────────────────────────────────────────
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
                if (type === 'pdf') {
                    lbImg.style.display = 'none';
                    lbPdf.style.display = 'block';
                    lbPdf.src = src;
                } else {
                    lbPdf.style.display = 'none';
                    lbImg.style.display = 'block';
                    lbImg.src = src;
                }
                lb.classList.add('is-open');
            }
        });

        var lbClose = document.getElementById('obLightboxClose');
        if (lbClose) {
            lbClose.onclick = function () {
                lb.classList.remove('is-open');
                if(lbPdf) lbPdf.src = '';
            };
        }
    }

    // ─────────────────────────────────────────────────────────
    // 3. INITIALIZE EVERYTHING ON PAGE LOAD
    // ─────────────────────────────────────────────────────────
    function initPreOfferForm() {
        if (!document.getElementById('obForm')) {
            return;
        }
        initDynamicDropdowns();
        initAdvancedUploads();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPreOfferForm);
    } else {
        initPreOfferForm();
    }

})();