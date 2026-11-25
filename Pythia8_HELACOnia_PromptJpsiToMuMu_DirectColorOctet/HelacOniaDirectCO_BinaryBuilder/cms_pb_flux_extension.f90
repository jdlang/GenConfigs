! Separate CMS Pb flux extension; upstream HELAC sources remain unchanged.
! Link with -Wl,--wrap=__photon_pdfs_MOD_epa_ion under the pinned CMS GCC12 ABI.
function cms_pb_flux(x, chargeZ) result(flux) bind(C, name="__wrap___photon_pdfs_MOD_epa_ion")
  use, intrinsic :: iso_c_binding, only: c_double, c_int
  implicit none
  real(c_double), intent(in) :: x
  integer(c_int), intent(in) :: chargeZ
  real(c_double) :: flux, xi
  real(c_double), parameter :: pi=3.14159265358979323846d0
  real(c_double), external :: bessk0, bessk1
  interface
    function upstream_flux(x, z) result(f) bind(C, name="__real___photon_pdfs_MOD_epa_ion")
      import c_double, c_int
      real(c_double), intent(in) :: x
      integer(c_int), intent(in) :: z
      real(c_double) :: f
    end function
  end interface
  if (chargeZ.ne.82) then
    flux=upstream_flux(x,chargeZ)
    return
  endif
  flux=0d0
  if (x.le.0d0.or.x.ge.1d0) return
  xi=x*0.9314d0*13.272d0/0.197d0
  flux=2d0*0.007297353080d0*82d0**2/(pi*x)* &
       (xi*bessk0(xi)*bessk1(xi)- &
        0.5d0*xi**2*(bessk1(xi)**2-bessk0(xi)**2))
  flux=max(0d0,flux)
end function
