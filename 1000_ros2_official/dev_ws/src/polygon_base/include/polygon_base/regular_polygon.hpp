#ifndef POLYGON_BASE_REGULAR_POLYGON_HPP
#define POLYGON_BASE_REGULAR_POLYGON_HPP

namespace polygon_base
{
class RegularPolygon
{
public:
  RegularPolygon() {}
  virtual ~RegularPolygon() {}

  virtual void initialize(double side_length) = 0;
  virtual double area() = 0;

protected:
  double side_length_;
};
}  // namespace polygon_base

#endif  // POLYGON_BASE_REGULAR_POLYGON_HPP
