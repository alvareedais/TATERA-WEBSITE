// Fungsi pemicu dropdown
        function toggleMenu(menuId, arrowId) {
            const menu = document.getElementById(menuId);
            const arrow = document.getElementById(arrowId);
            if (menu && arrow) {
                menu.classList.toggle('hidden');
                arrow.classList.toggle('rotate-90');
            }
        }

        // FUNGSI UTAMA: Menyalakan menu aktif otomatis berdasarkan nama file URL
        document.addEventListener("DOMContentLoaded", function() {
            // Ambil nama file html yang sedang aktif saat ini (contoh: "pengaturan.html")
            const currentPath = window.location.pathname.split("/").pop();
            
            // Cari semua elemen tautan menu yang memiliki class 'nav-link'
            const navLinks = document.querySelectorAll('.nav-link');

            navLinks.forEach(link => {
                // Ambil nilai attribute href dari menu (contoh: "pengaturan.html")
                const linkHref = link.getAttribute('href');

                if (currentPath === linkHref) {
                    // JIKA cocok, hilangkan warna abu-abu default bawaan
                    link.classList.remove('text-gray-600', 'text-gray-500', 'hover:bg-gray-100');
                    
                    // TAMBAHKAN warna hijau aktif bersinar & shadow sesuai gambar desain
                    link.classList.add('bg-[#39B54A]', 'text-white', 'shadow-sm');

                    // OTOMATIS BUKA DROPDOWN JIKA MENU AKTIF BERADA DI DALAM SUB-MENU
                    const parentContainer = link.closest('[id^="menu-"]');
                    if (parentContainer) {
                        parentContainer.classList.remove('hidden'); // buka list menu
                        
                        // putar anak panah dropdown-nya agar menghadap ke bawah
                        const parentId = parentContainer.getAttribute('id');
                        const arrowId = parentId.replace('menu-', 'arrow-');
                        const arrowIcon = document.getElementById(arrowId);
                        if (arrowIcon) arrowIcon.classList.add('rotate-90');
                    }
                }
            });
            
            // Panggil sapaan profil
            const nama = localStorage.getItem('user_nama_lengkap') || 'Adam Permana';
            document.getElementById('sidebar-username').innerText = "Hi, " + nama.split(" ")[0];
        });