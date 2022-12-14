!> Various definitions and tools for initializing NGA2 config
module geometry
   use config_class, only: config
   use precision,    only: WP
   implicit none
   private
   
   !> Single config
   type(config), public :: cfg
   
   public :: geometry_init
   
   ! Vessel geometry will be needed in BCs
   real(WP), public :: Lv,IR,dx,dy,dz
   real(WP), public :: ypipe,rpipe,lpipe
   
contains
   
   
   !> Initialization of problem geometry
   subroutine geometry_init
      use sgrid_class, only: sgrid
      use param,       only: param_read
      implicit none
      type(sgrid) :: grid
      
      
      ! Create a grid from input params
      create_grid: block
         use sgrid_class, only: cartesian
         integer :: i,j,k,nx,ny,nz
         real(WP) :: Lx,Ly,Lz
         real(WP), dimension(:), allocatable :: x,y,z
         
         ! Read in grid definition
         call param_read('Lx',Lx); call param_read('nx',nx); allocate(x(nx+1))
         call param_read('Ly',Ly); call param_read('ny',ny); allocate(y(ny+1))
         call param_read('Lz',Lz); call param_read('nz',nz); allocate(z(nz+1))
         
         ! Create simple rectilinear grid
         do i=1,nx+1
            x(i)=real(i-1,WP)/real(nx,WP)*Lx-0.5_WP*Lx
         end do
         do j=1,ny+1
            y(j)=real(j-1,WP)/real(ny,WP)*Ly-0.5_WP*Ly
         end do
         do k=1,nz+1
            z(k)=real(k-1,WP)/real(nz,WP)*Lz-0.5_WP*Lz
         end do
         dx=x(2)-x(1)
         dy=y(2)-y(1)
         dz=z(2)-z(1)
         
         ! General serial grid object
         grid=sgrid(coord=cartesian,no=2,x=x,y=y,z=z,xper=.false.,yper=.false.,zper=.false.,name='PressureVessel')
         
      end block create_grid
      
      
      ! Create a config from that grid on our entire group
      create_cfg: block
         use parallel, only: group
         integer, dimension(3) :: partition
         
         ! Read in partition
         call param_read('Partition',partition,short='p')
         
         ! Create partitioned grid
         cfg=config(grp=group,decomp=partition,grid=grid)
         
      end block create_cfg
      
      
      ! Create masks for this config
      create_walls: block
         integer :: i,j,k
         real(WP) :: r
         ! Read in vessel dimensions
         call param_read('Vessel length',Lv)
         call param_read('Vessel inner radius',IR)
         ! Read in inlet pipe geometry
         call param_read('Inlet pipe position',ypipe)
         call param_read('Inlet pipe radius'  ,rpipe)
         call param_read('Inlet pipe length'  ,lpipe)
         ! Start from no fluid
         cfg%VF=0.0_WP
         ! Carve out the inside of the vessel
         do k=cfg%kmino_,cfg%kmaxo_
            do j=cfg%jmino_,cfg%jmaxo_
               do i=cfg%imino_,cfg%imaxo_
                  r=sqrt(cfg%ym(j)**2+cfg%zm(k)**2)
                  if (cfg%xm(i).gt.-0.5_WP*Lv.and.cfg%xm(i).lt.+0.5_WP*Lv.and.r.lt.IR) cfg%VF(i,j,k)=1.0_WP
               end do
            end do
         end do
         ! Add a pipe-like wall at the bottom - now with a square cylinder
         do k=cfg%kmino_,cfg%kmaxo_
            do j=cfg%jmino_,cfg%jmaxo_
               do i=cfg%imino_,cfg%imaxo_
                  if (cfg%xm(i).gt.-0.5_WP*lpipe.and.cfg%xm(i).lt.+0.5_WP*lpipe.and.abs(cfg%ym(j)-ypipe).lt.rpipe.and.abs(cfg%zm(k)).lt.rpipe) cfg%VF(i,j,k)=0.0_WP
               end do
            end do
         end do
      end block create_walls
      
      
      ! Finally, write out config file
      call cfg%write('config')
      
      
   end subroutine geometry_init
   
   
end module geometry
